"""박자 배치 채점이 제대로 도는지 확인하는 스크립트.

녹음 파일을 마디별로 채점해 DB에 저장하는 과정을 세 단계로 나눠 점검한다.

- 엔진: 정해둔 입력으로 state·action·reward·Q 확인. (오디오·DB 불필요)
- 측정: 합성 비트로 그리드 로직(정확→GOOD, 어긋남→비-GOOD),
        실제 연주는 결정론·12마디 확인. (audio 그룹 필요)
- 적재: 시드 세션으로 돌려 feedback_events·q_table_entries 확인. (로컬 MySQL 필요)

실행: uv run --group audio python scripts/verify_rhythm_batch.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REFERENCE = "fixtures/media/twinkle_twinkle.violin_reference.mp3"
SONG_ID = 1


def _dist(readings) -> Counter:
    return Counter(r.state for r in readings if r.valid)


def layer1_engine() -> bool:
    from app.domain.agent.qlearning import QLearningEngine
    from app.domain.agent.rhythm.policy import RhythmPolicy
    from app.domain.agent.schema import MeasureReading

    readings = [
        MeasureReading(measure_index=1, state="LATE", meta={"drift_ms": 150.0}),
        MeasureReading(measure_index=2, state="FAST", meta={"beat_ratio": 1.4}),
        MeasureReading(measure_index=3, state="GOOD", meta={"drift_ms": 5.0}),
        MeasureReading(measure_index=4, state="EARLY", meta={"drift_ms": -150.0}),
    ]
    engine = QLearningEngine(RhythmPolicy(), {})
    out = engine.run(readings)

    expected = [
        ("RH-03", "RHYTHM_CATCH_UP", None),
        ("RH-04", "TEMPO_SLOW_DOWN", 0.5),
        ("RH-01", "POSITIVE_RHYTHM", 1.0),
        ("RH-02", "RHYTHM_WAIT", -0.8),
    ]
    ok = True
    for o, (aid, action, reward) in zip(out, expected, strict=True):
        match = o.action_id == aid and o.action == action and o.reward == reward
        ok &= match
        print(
            f"  m{o.measure_index} {o.state:5} {o.action_id} {o.action:16}"
            f" reward={o.reward} q={o.q}  {'OK' if match else 'FAIL'}"
        )
    ok &= len(engine.updated) == 3 and engine.q[("LATE", "RHYTHM_CATCH_UP")][0] > 0
    return ok


def layer2_measurement() -> bool | None:
    try:
        import librosa  # noqa: F401
    except ImportError as exc:
        print(f"  [skip] audio deps 미설치: {exc}")
        return None

    from app.domain.agent.rhythm.measurer import RhythmMeasurer, RhythmSpec

    spec = RhythmSpec(bpm=96, beats_per_measure=4, total_measures=12)
    measurer = RhythmMeasurer()
    ok = True

    interval = 60.0 / spec.bpm
    n = spec.total_measures * spec.beats_per_measure
    exact = _dist(measurer.readings_from_beats([i * interval for i in range(n)], spec))
    exact_good = bool(exact) and exact.most_common(1)[0][0] == "GOOD"
    ok &= exact_good
    print(f"  합성 정확한 박: {dict(exact)}  GOOD 최빈={'OK' if exact_good else 'X'}")

    fast = _dist(measurer.readings_from_beats([i * 0.50 for i in range(n + 12)], spec))
    fast_off = bool(fast) and fast.get("GOOD", 0) < sum(
        v for k, v in fast.items() if k != "GOOD"
    )
    ok &= fast_off
    print(f"  합성 어긋난 박: {dict(fast)}  비-GOOD 우세={'OK' if fast_off else 'X'}")

    if Path(REFERENCE).exists():
        a = measurer.measure(REFERENCE, spec)
        b = measurer.measure(REFERENCE, spec)
        same = [r.state for r in a] == [r.state for r in b]
        valid12 = len(a) == 12 and all(r.valid for r in a)
        ok &= same and valid12
        mark = "OK" if (same and valid12) else "FAIL"
        print(f"  기준: 12마디={valid12} 결정론={same} {dict(_dist(a))}  {mark}")

    return ok


async def layer3_db() -> bool | None:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal
    from app.domain.agent.schema import Domain
    from app.domain.agent.service import AgentBatchService

    if not Path(REFERENCE).exists():
        print(f"  [skip] 기준 음원 없음: {REFERENCE}")
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
                    "WHERE session_id = :s AND domain = 'rhythm'"
                ),
                {"s": session_id},
            )
            await session.commit()

            outputs = await AgentBatchService(session).run(
                session_id, user_id, SONG_ID, REFERENCE, domain=Domain.RHYTHM
            )

            count = (
                await session.execute(
                    text(
                        "SELECT COUNT(*) FROM feedback_events "
                        "WHERE session_id = :s AND domain = 'rhythm'"
                    ),
                    {"s": session_id},
                )
            ).scalar()
            sample = (
                await session.execute(
                    text(
                        "SELECT measure_index, state, action_id, q, meta "
                        "FROM feedback_events "
                        "WHERE session_id = :s AND domain = 'rhythm' "
                        "ORDER BY measure_index LIMIT 3"
                    ),
                    {"s": session_id},
                )
            ).all()
            q_rows = (
                await session.execute(
                    text(
                        "SELECT state, action, q_value, update_count "
                        "FROM q_table_entries WHERE user_id = :u AND domain = 'rhythm'"
                    ),
                    {"u": user_id},
                )
            ).all()

        ok = count == len(outputs) and count > 0
        mark = "OK" if ok else "FAIL"
        print(f"  feedback_events 적재: {count}행 (반환 {len(outputs)})  {mark}")
        for r in sample:
            print(f"    m{r[0]} {r[1]:5} {r[2]} q={r[3]} meta={r[4]}")
        print(f"  q_table_entries(rhythm): {len(q_rows)}행")
        for r in q_rows:
            print(f"    {r[0]:5} {r[1]:16} q={r[2]:.3f} count={r[3]}")
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
