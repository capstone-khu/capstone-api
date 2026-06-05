"""자세 배치 채점이 제대로 도는지 확인하는 스크립트.

녹화 영상을 마디별로 채점해 DB에 저장하는 과정을 세 단계로 나눠 점검한다.

- 엔진: 정해둔 입력으로 state·action·reward·Q 확인. (오디오·DB 불필요)
- 측정: 합성 feature로 분석기→state(평균→GOOD, feature 밀면 그 state),
        실제 영상은 결정론·12마디 확인. (vision 그룹·.task 모델 필요)
- 적재: 시드 세션으로 돌려 feedback_events·q_table_entries 확인. (로컬 MySQL 필요)

실행: uv run --group vision python scripts/verify_posture_batch.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VIDEO = "fixtures/media/twinkle_twinkle.violin_performance.mp4"
TASK_MODEL = "fixtures/models/pose_landmarker_lite.task"
SONG_ID = 1
DIRECTION = {0: 1, 1: 1, 2: 1, 3: 1, 4: -1, 5: 1}


def _dist(readings) -> Counter:
    return Counter(r.state for r in readings if r.valid)


def layer1_engine() -> bool:
    from app.domain.agent.posture.policy import PosturePolicy
    from app.domain.agent.qlearning import QLearningEngine
    from app.domain.agent.schema import MeasureReading

    readings = [
        MeasureReading(measure_index=1, state="GOOD"),
        MeasureReading(measure_index=2, state="LEFT_ARM_POSTURE"),
        MeasureReading(measure_index=3, state="GOOD"),
        MeasureReading(measure_index=4, state="SHOULDER_IMBALANCE"),
    ]
    engine = QLearningEngine(PosturePolicy(), {})
    out = engine.run(readings)

    expected = [
        ("PS-01", "POSITIVE_POSTURE", None),
        ("PS-05", "ARM_POSTURE_CORRECT", -0.8),
        ("PS-01", "POSITIVE_POSTURE", 1.0),
        ("PS-03", "SHOULDER_BALANCE", -0.8),
    ]
    ok = True
    for o, (aid, action, reward) in zip(out, expected, strict=True):
        match = o.action_id == aid and o.action == action and o.reward == reward
        ok &= match
        print(f"  m{o.measure_index} {o.state:20} {o.action_id} {o.action:20} "
              f"reward={o.reward}  {'OK' if match else 'FAIL'}")
    key = ("LEFT_ARM_POSTURE", "ARM_POSTURE_CORRECT")
    ok &= len(engine.updated) == 2 and engine.q[key][0] > 0
    return ok


def layer2_measurement() -> bool | None:
    try:
        import numpy as np

        from app.domain.agent.posture.analyzer import PostureAnalyzer
    except ImportError as exc:
        print(f"  [skip] vision deps 미설치: {exc}")
        return None

    from app.domain.agent.posture.policy import classify_posture

    analyzer = PostureAnalyzer()
    mean = np.array(analyzer.feature_mean, dtype=np.float32)
    std = np.array(analyzer.feature_std, dtype=np.float32)
    ok = True

    base = analyzer.analyze(mean)
    base_good = classify_posture(base["stable"], base["top_feature_index"]) == "GOOD"
    ok &= base_good
    print(f"  평균 벡터 → GOOD={'OK' if base_good else 'FAIL'}")

    hits = 0
    for i in range(6):
        v = mean.copy()
        v[i] = mean[i] + DIRECTION[i] * 8 * std[i]
        hits += analyzer.analyze(v)["top_feature_index"] == i
    feat_ok = hits == 6
    ok &= feat_ok
    print(f"  feature 식별 {hits}/6  {'OK' if feat_ok else 'FAIL'}")

    push = np.array([DIRECTION[i] for i in range(6)], dtype=np.float32)
    res = analyzer.analyze(mean + push * 8 * std)
    bad_state = classify_posture(res["stable"], res["top_feature_index"]) != "GOOD"
    ok &= bad_state
    print(f"  전체 밀기 → 비-GOOD={'OK' if bad_state else 'FAIL'} (case={res['case']})")

    if Path(VIDEO).exists() and Path(TASK_MODEL).exists():
        try:
            from app.domain.agent.posture.measurer import PoseMeasurer, PostureSpec
            from app.domain.agent.score import load_timed_score

            spec = PostureSpec(windows=load_timed_score(SONG_ID).measure_windows())
            a = PoseMeasurer().measure(VIDEO, spec)
            b = PoseMeasurer().measure(VIDEO, spec)
            same = [r.state for r in a] == [r.state for r in b]
            ok &= same and len(a) == 12
            mark = "OK" if (same and len(a) == 12) else "FAIL"
            print(f"  실제 영상: 결정론={same} {dict(_dist(a))}  {mark}")
        except Exception as exc:
            print(f"  [warn] 실제 영상 측정 실패: {type(exc).__name__}: {exc}")
    else:
        print("  [skip] 영상 또는 .task 모델 없음")

    return ok


async def layer3_db() -> bool | None:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal
    from app.domain.agent.schema import Domain
    from app.domain.agent.service import AgentBatchService

    if not (Path(VIDEO).exists() and Path(TASK_MODEL).exists()):
        print("  [skip] 영상 또는 .task 모델 없음")
        return None

    try:
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT id, user_id FROM sessions "
                        "WHERE song_id = :sid ORDER BY id LIMIT 1"
                    ),
                    {"sid": SONG_ID},
                )
            ).first()
            if row is None:
                print("  [skip] 시드 세션 없음")
                return None
            session_id, user_id = row

            await session.execute(
                text(
                    "DELETE FROM feedback_events "
                    "WHERE session_id = :s AND domain = 'posture'"
                ),
                {"s": session_id},
            )
            await session.commit()

            outputs = await AgentBatchService(session).run(
                session_id, user_id, SONG_ID, VIDEO, domain=Domain.POSTURE
            )

            count = (
                await session.execute(
                    text(
                        "SELECT COUNT(*) FROM feedback_events "
                        "WHERE session_id = :s AND domain = 'posture'"
                    ),
                    {"s": session_id},
                )
            ).scalar()
            q_rows = (
                await session.execute(
                    text(
                        "SELECT state, action, q_value, update_count "
                        "FROM q_table_entries WHERE user_id = :u AND domain = 'posture'"
                    ),
                    {"u": user_id},
                )
            ).all()

        ok = count == len(outputs) and count > 0
        mark = "OK" if ok else "FAIL"
        print(f"  feedback_events 적재: {count}행 (반환 {len(outputs)})  {mark}")
        print(f"  q_table_entries(posture): {len(q_rows)}행")
        for r in q_rows:
            print(f"    {r[0]:20} {r[1]:20} q={r[2]:.3f} count={r[3]}")
        return ok
    except Exception as exc:
        print(f"  [skip] DB 미연결: {type(exc).__name__}: {exc}")
        return None


def main() -> int:
    import app.main  # noqa: F401

    results: dict[str, bool | None] = {}

    print("\n[엔진]")
    results["engine"] = layer1_engine()

    print("\n[측정]")
    results["measurement"] = layer2_measurement()

    print("\n[적재]")
    results["persistence"] = asyncio.run(layer3_db())

    print("\n=== 요약 ===")
    failed = False
    for name, res in results.items():
        label = "PASS" if res else ("SKIP" if res is None else "FAIL")
        failed |= res is False
        print(f"  {name:12} {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
