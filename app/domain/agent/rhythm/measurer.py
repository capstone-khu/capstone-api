from dataclasses import dataclass
from typing import Protocol

from app.domain.agent.rhythm.policy import GOOD, RhythmPolicy, classify_rhythm
from app.domain.agent.schema import Domain, MeasureReading

TRIM_TOP_DB = 28

_policy = RhythmPolicy()


class BeatDetector(Protocol):
    def detect(self, audio_path: str) -> list[float]: ...


class LibrosaBeatDetector:
    """librosa.beat.beat_track 기반 비트 검출(검출 시각 초 단위).

    프로토타입은 madmom 을 썼지만 py3.12+numpy2 에서 설치가 안 돼(환경 통합)
    연동에선 librosa 로 대체. 같은 인터페이스라 호환 환경이 생기면 이 자리만 교체한다.
    """

    def detect(self, audio_path: str) -> list[float]:
        import librosa

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
        return [float(b) for b in beats]


@dataclass
class RhythmSpec:
    bpm: float
    beats_per_measure: int
    total_measures: int


class RhythmMeasurer:
    """녹음 오디오 + 박자 스펙(bpm·박자·마디) → 마디별 박자 측정(MeasureReading).

    프로토타입(beat-agent)의 그리드 드리프트·score 산출을 옮긴 것.
    비트 검출만 BeatDetector(기본 librosa)로 분리해 madmom 으로 교체 가능하게 뒀다.
    """

    domain = Domain.RHYTHM

    def __init__(self, detector: BeatDetector | None = None) -> None:
        self.detector = detector or LibrosaBeatDetector()

    def measure(self, audio_path: str, spec: RhythmSpec) -> list[MeasureReading]:
        import librosa

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        _, idx = librosa.effects.trim(y, top_db=TRIM_TOP_DB)
        audio_start = idx[0] / sr
        beats = [b for b in self.detector.detect(audio_path) if b >= audio_start]
        return self.readings_from_beats(beats, spec)

    def readings_from_beats(
        self, beats: list[float], spec: RhythmSpec
    ) -> list[MeasureReading]:
        import numpy as np

        beat_interval = 60.0 / spec.bpm
        half = spec.beats_per_measure // 2
        if not beats:
            return [
                MeasureReading(measure_index=m + 1, state=GOOD, valid=False, meta={})
                for m in range(spec.total_measures)
            ]

        beats = np.array(beats)
        anchor = float(beats[0])
        total_beats = spec.total_measures * spec.beats_per_measure
        grid = anchor + np.arange(total_beats) * beat_interval

        readings: list[MeasureReading] = []
        for m in range(spec.total_measures):
            halves = []
            for h in range(2):
                offset = (m * spec.beats_per_measure + h * half) * beat_interval
                t_start = anchor + offset
                t_end = t_start + half * beat_interval
                grid_seg = grid[(grid >= t_start) & (grid < t_end)]
                beats_seg = beats[(beats >= t_start) & (beats < t_end)]
                halves.append(self._eval_half(grid_seg, beats_seg, beat_interval))
            readings.append(self._aggregate(m + 1, halves))
        return readings

    def _eval_half(self, grid_seg, beats_seg, beat_interval: float) -> dict:
        import numpy as np

        if len(grid_seg) == 0 or len(beats_seg) == 0:
            return {"valid": False, "state": GOOD}

        signed = [
            float(beats_seg[int(np.argmin(np.abs(beats_seg - g)))] - g)
            for g in grid_seg
        ]
        mean_drift = float(np.mean(signed))
        rel = [abs(s - mean_drift) / beat_interval for s in signed]
        score = float(np.exp(-np.mean(rel) * 3))
        drift_ms = mean_drift * 1000
        beat_ratio = len(beats_seg) / len(grid_seg)
        return {
            "valid": True,
            "state": classify_rhythm(score, drift_ms, beat_ratio),
            "drift_ms": round(drift_ms, 1),
            "score": round(score, 3),
            "beat_ratio": round(beat_ratio, 3),
        }

    def _aggregate(self, measure_index: int, halves: list[dict]) -> MeasureReading:
        valid = [h for h in halves if h["valid"]]
        if not valid:
            return MeasureReading(
                measure_index=measure_index,
                state=GOOD,
                valid=False,
                meta={"halves": [h["state"] for h in halves]},
            )

        worst = max(valid, key=lambda h: _policy.severity(h["state"]))
        return MeasureReading(
            measure_index=measure_index,
            state=worst["state"],
            valid=True,
            meta={
                "drift_ms": round(sum(h["drift_ms"] for h in valid) / len(valid), 1),
                "score": round(min(h["score"] for h in valid), 3),
                "halves": [h["state"] for h in halves],
            },
        )
