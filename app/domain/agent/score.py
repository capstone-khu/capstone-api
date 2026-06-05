import json
from math import log2
from pathlib import Path

SEED_SCORE: dict[int, str] = {
    1: "seeds/song/twinkle_twinkle.raw.json",
}


class Score:
    """시간축 score 메타데이터(음표별 start/end/hz_exact/measure) 래퍼.

    프레임 타임스탬프 → 목표 음표·cents 편차(옥타브 정규화 포함)를 제공한다.
    """

    def __init__(self, notes: list[dict]) -> None:
        self.notes = notes

    def target_at(self, timestamp: float) -> dict | None:
        for note in self.notes:
            if note["start"] <= timestamp < note["end"]:
                return note
        return None

    def cents_at(self, actual_hz: float, timestamp: float) -> float | None:
        target = self.target_at(timestamp)
        if target is None or actual_hz <= 0:
            return None
        target_hz = target["hz_exact"]
        if target_hz <= 0:
            return None
        normalized = self._normalize_octave(actual_hz, target_hz)
        return 1200.0 * log2(normalized / target_hz)

    def measures(self) -> list[int]:
        return sorted({n["measure"] for n in self.notes if n.get("measure")})

    def measure_windows(self) -> list[tuple[int, float, float]]:
        by_measure: dict[int, list[dict]] = {}
        for note in self.notes:
            m = note.get("measure")
            if m is not None:
                by_measure.setdefault(m, []).append(note)

        measures = sorted(by_measure)
        windows: list[tuple[int, float, float]] = []
        for i, m in enumerate(measures):
            start = min(n["start"] for n in by_measure[m])
            if i + 1 < len(measures):
                end = min(n["start"] for n in by_measure[measures[i + 1]])
            else:
                end = max(n["end"] for n in by_measure[m])
            windows.append((m, round(start, 3), round(end, 3)))
        return windows

    @staticmethod
    def _normalize_octave(actual_hz: float, target_hz: float) -> float:
        normalized = actual_hz
        while normalized < target_hz / 1.5:
            normalized *= 2
        while normalized > target_hz * 1.5:
            normalized /= 2
        return normalized


def load_timed_score(song_id: int) -> Score:
    path = SEED_SCORE.get(song_id)
    if path is None:
        raise ValueError(f"시간축 score 메타데이터가 없는 곡입니다: song_id={song_id}")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Score(data["notes"])
