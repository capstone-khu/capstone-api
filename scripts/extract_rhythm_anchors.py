"""기준 음원에서 박자 앵커(마디별 기대 onset)를 추출해 시드 JSON 으로 저장하는 스크립트.

시간축 악보(raw.json)의 음표 시각으로 탐색창을 잡고(반경 = 이웃 음표 간격의 절반,
최대 SEARCH_RADIUS_S), 기준 음원 onset 강도의 최강 국소 피크를 앵커로 기록한다.
채점은 연주에서 같은 검출기로 뽑은 피크를 앵커와 비교하므로 검출 편향이 상쇄된다(#55).
게이트를 못 넘는 음표(짧은 음 등)는 기준에서도 측정 불가이므로 앵커에서 제외한다.

실행: uv run --group audio python scripts/extract_rhythm_anchors.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SONGS: dict[int, dict] = {
    1: {
        "audio": "fixtures/media/twinkle_twinkle.violin_reference.mp3",
        "out": "seeds/song/twinkle_twinkle.rhythm_anchors.json",
    },
}


def search_radius(starts: list[float], idx: int, max_radius: float) -> float:
    radius = max_radius
    if idx > 0:
        radius = min(radius, (starts[idx] - starts[idx - 1]) / 2)
    if idx < len(starts) - 1:
        radius = min(radius, (starts[idx + 1] - starts[idx]) / 2)
    return radius


def extract(song_id: int, audio: str, out: str) -> None:
    from app.domain.agent.rhythm.measurer import (
        SEARCH_RADIUS_S,
        LibrosaOnsetDetector,
    )
    from app.domain.agent.score import load_timed_score

    score = load_timed_score(song_id)
    windows = score.measure_windows()
    env = LibrosaOnsetDetector().envelope_from_file(audio)

    starts = sorted((n["start"], n["measure"]) for n in score.notes)
    times = [t for t, _ in starts]

    anchors, dropped = [], []
    for i, (t, m) in enumerate(starts):
        radius = search_radius(times, i, SEARCH_RADIUS_S)
        peak = env.strongest_in(t, radius)
        if peak is None:
            dropped.append((m, t))
            continue
        anchors.append(
            {"measure": m, "time": round(peak, 3), "radius": round(radius, 3)}
        )

    payload = {
        "source_audio": audio,
        "windows": [{"measure": m, "start": s, "end": e} for m, s, e in windows],
        "anchors": anchors,
    }
    Path(out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[song {song_id}] {audio}")
    print(f"  앵커 {len(anchors)}/{len(starts)}개 → {out}")
    for m, t in dropped:
        print(f"  제외: m{m} t={t:.2f}s (게이트 미달)")


def main() -> None:
    for song_id, paths in SONGS.items():
        extract(song_id, paths["audio"], paths["out"])


if __name__ == "__main__":
    main()
