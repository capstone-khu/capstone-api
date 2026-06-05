"""음정 배치 채점이 제대로 도는지 확인하는 스크립트.

녹음 파일 하나를 마디별로 채점해 DB에 쌓는 과정을 세 단계로 나눠 점검한다.

- 엔진: 정해둔 입력을 넣어 state·action·reward·Q가 의도대로 나오는지 본다.
- 측정: 기준 연주를 다시 넣으면 대부분 GOOD이 나오고, 음을 일부러 올리고 내리면
        SHARP·FLAT이 나오는 지 본다. (audio 그룹 필요)
- 적재: 시드 세션으로 실제로 돌려 feedback_events·q_table_entries에 쌓이는지 본다.

실행: uv run --group audio python scripts/verify_pitch_batch.py
오디오 그룹이나 DB가 없으면 그 단계는 건너뛴다. 엔진 단계는 항상 돈다.
"""

import asyncio
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REFERENCE = "fixtures/media/twinkle_twinkle.violin_reference.mp3"
PERFORMANCE = "fixtures/media/twinkle_twinkle.violin_performance.mp4"
SONG_ID = 1


def _dist(readings) -> Counter:
    return Counter(r.state for r in readings if r.valid)


def layer1_engine() -> bool:
    from app.domain.agent.pitch.policy import PitchPolicy
    from app.domain.agent.qlearning import QLearningEngine
    from app.domain.agent.schema import MeasureReading

    readings = [
        MeasureReading(measure_index=1, state="FLAT_MAJOR", meta={"avg_cents": -150.0}),
        MeasureReading(measure_index=2, state="FLAT_SLIGHT", meta={"avg_cents": -50.0}),
        MeasureReading(measure_index=3, state="GOOD", meta={"avg_cents": 5.0}),
        MeasureReading(measure_index=4, state="SHARP_MAJOR", meta={"avg_cents": 150.0}),
    ]
    engine = QLearningEngine(PitchPolicy(), {})
    out = engine.run(readings)

    expected = [
        ("PT-02", "PITCH_UP", None),
        ("PT-02", "PITCH_UP", 0.5),
        ("PT-01", "POSITIVE_PITCH", 1.0),
        ("PT-03", "PITCH_DOWN", -0.8),
    ]
    ok = True
    for o, (aid, action, reward) in zip(out, expected, strict=True):
        match = o.action_id == aid and o.action == action and o.reward == reward
        ok &= match
        print(
            f"  m{o.measure_index} {o.state:12} {o.action_id} {o.action:16}"
            f" reward={o.reward} q={o.q}  {'OK' if match else 'FAIL'}"
        )
    ok &= out[0].reward is None and out[3].meta == {"avg_cents": 150.0}
    ok &= len(engine.updated) == 3 and engine.q[("FLAT_MAJOR", "PITCH_UP")][0] > 0
    return ok


def _measure(path: str, score):
    from app.domain.agent.pitch.measurer import PitchMeasurer

    return PitchMeasurer().measure(path, score)


def layer2_measurement() -> bool | None:
    try:
        import librosa
        import soundfile as sf
    except ImportError as exc:
        print(f"  [skip] audio deps 미설치: {exc}")
        return None

    from app.domain.agent.pitch.measurer import SAMPLE_RATE
    from app.domain.agent.score import load_timed_score

    score = load_timed_score(SONG_ID)
    ok = True

    if not Path(REFERENCE).exists():
        print(f"  [skip] 기준 음원 없음: {REFERENCE}")
        return None

    ref = _measure(REFERENCE, score)
    ref_dist = _dist(ref)
    good_is_top = bool(ref_dist) and ref_dist.most_common(1)[0][0] == "GOOD"
    ok &= good_is_top
    mark = "OK" if good_is_top else "FAIL"
    print(f"  자기일치 분포: {dict(ref_dist)}  GOOD 최빈={mark}")

    y, sr = librosa.load(REFERENCE, sr=SAMPLE_RATE, mono=True)
    shifts = [(0.5, "+50cents", "SHARP"), (-1.2, "-120cents", "FLAT")]
    for steps, label, group in shifts:
        shifted = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=steps)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, shifted, sr)
            dist = _dist(_measure(tmp.name, score))
        shifted_to = sum(v for k, v in dist.items() if k.startswith(group))
        good = dist.get("GOOD", 0)
        moved = shifted_to > good
        ok &= moved
        print(
            f"  시프트 {label}: {dict(dist)}  {group} 우세={'OK' if moved else 'FAIL'}"
        )

    if Path(PERFORMANCE).exists():
        try:
            perf_dist = _dist(_measure(PERFORMANCE, score))
            varied = len(perf_dist) >= 2
            ok &= varied
            mark = "OK" if varied else "FAIL"
            print(f"  사용자 연주 분포: {dict(perf_dist)}  다양성={mark}")
        except Exception as exc:
            print(f"  [warn] 사용자 연주 측정 실패(ffmpeg 등): {exc}")

    return ok


async def layer3_db() -> bool | None:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal
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
                text("DELETE FROM feedback_events WHERE session_id = :s"),
                {"s": session_id},
            )
            await session.commit()

            outputs = await AgentBatchService(session).run(
                session_id, user_id, SONG_ID, REFERENCE
            )

            count = (
                await session.execute(
                    text("SELECT COUNT(*) FROM feedback_events WHERE session_id = :s"),
                    {"s": session_id},
                )
            ).scalar()
            sample = (
                await session.execute(
                    text(
                        "SELECT measure_index, state, action_id, q, meta "
                        "FROM feedback_events WHERE session_id = :s "
                        "ORDER BY measure_index LIMIT 3"
                    ),
                    {"s": session_id},
                )
            ).all()
            q_rows = (
                await session.execute(
                    text(
                        "SELECT state, action, q_value, update_count "
                        "FROM q_table_entries WHERE user_id = :u AND domain = 'pitch'"
                    ),
                    {"u": user_id},
                )
            ).all()

        ok = count == len(outputs) and count > 0
        mark = "OK" if ok else "FAIL"
        print(f"  feedback_events 적재: {count}행 (반환 {len(outputs)})  {mark}")
        for r in sample:
            print(f"    m{r[0]} {r[1]:12} {r[2]} q={r[3]} meta={r[4]}")
        print(f"  q_table_entries(pitch): {len(q_rows)}행")
        for r in q_rows:
            print(f"    {r[0]:12} {r[1]:16} q={r[2]:.3f} count={r[3]}")
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
