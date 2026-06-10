import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.domain.agent.rhythm.policy import GOOD, RhythmPolicy, classify_rhythm
from app.domain.agent.schema import Domain, MeasureReading

EVAL_SAMPLE_RATE = 16000
HOP_LENGTH = 256
SEARCH_RADIUS_S = 0.25
GATE_RATIO = 1.5

SEED_ANCHORS: dict[int, str] = {
    1: "seeds/song/twinkle_twinkle.rhythm_anchors.json",
}

_policy = RhythmPolicy()


class OnsetEnvelope:
    """onset 강도 국소 피크(게이트 통과분)의 시각 질의를 제공.

    게이트는 전체 강도 중앙값 x GATE_RATIO — 무음 입력이면 피크가 없다.
    """

    def __init__(self, times, strengths) -> None:
        import numpy as np

        times = np.asarray(times, dtype=float)
        strengths = np.asarray(strengths, dtype=float)
        peak = np.zeros(len(strengths), dtype=bool)
        if len(strengths) > 2:
            peak[1:-1] = (strengths[1:-1] >= strengths[:-2]) & (
                strengths[1:-1] >= strengths[2:]
            )
        gate = float(np.median(strengths)) * GATE_RATIO
        ok = peak & (strengths >= gate) & (strengths > 0)
        self.peak_times = times[ok]
        self.peak_strengths = strengths[ok]

    def strongest_in(self, center: float, radius: float) -> float | None:
        import numpy as np

        mask = np.abs(self.peak_times - center) <= radius
        if not mask.any():
            return None
        ts = self.peak_times[mask]
        return float(ts[int(np.argmax(self.peak_strengths[mask]))])

    def nearest_to(self, center: float, radius: float) -> float | None:
        import numpy as np

        mask = np.abs(self.peak_times - center) <= radius
        if not mask.any():
            return None
        ts = self.peak_times[mask]
        return float(ts[int(np.argmin(np.abs(ts - center)))])

    def count_in(self, start: float, end: float) -> int:
        return int(((self.peak_times >= start) & (self.peak_times < end)).sum())


class OnsetDetector(Protocol):
    def envelope(self, samples, sr: int, t0: float = 0.0) -> OnsetEnvelope: ...

    def envelope_from_file(self, audio_path: str) -> OnsetEnvelope: ...


class LibrosaOnsetDetector:
    """librosa onset_strength(spectral flux) 기반 onset envelope 산출.

    envelope 는 메모리 샘플(실시간), envelope_from_file 은 파일(배치) 입력.
    이음줄(legato) 곡에서 피크가 약해지면 f0 보조 검출기로 이 자리만 교체한다.
    """

    def envelope(self, samples, sr: int, t0: float = 0.0) -> OnsetEnvelope:
        import librosa

        strengths = librosa.onset.onset_strength(
            y=samples, sr=sr, hop_length=HOP_LENGTH
        )
        times = librosa.times_like(strengths, sr=sr, hop_length=HOP_LENGTH) + t0
        return OnsetEnvelope(times, strengths)

    def envelope_from_file(self, audio_path: str) -> OnsetEnvelope:
        import librosa

        y, sr = librosa.load(audio_path, sr=EVAL_SAMPLE_RATE, mono=True)
        return self.envelope(y, sr)


@dataclass
class Anchor:
    time: float
    radius: float


@dataclass
class RhythmSpec:
    """마디 윈도우 + 기준 음원에서 추출한 마디별 앵커(기대 onset).

    앵커는 scripts/extract_rhythm_anchors.py 로 사전 추출한 시드를 쓴다.
    기준-연주 양쪽을 같은 검출기로 재서 검출 편향을 상쇄한다(#55).
    """

    windows: list[tuple[int, float, float]]
    anchors: dict[int, list[Anchor]]

    @classmethod
    def load(cls, song_id: int) -> "RhythmSpec":
        path = SEED_ANCHORS.get(song_id)
        if path is None:
            raise ValueError(f"박자 앵커 시드가 없는 곡입니다: song_id={song_id}")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        windows = [(w["measure"], w["start"], w["end"]) for w in data["windows"]]
        anchors: dict[int, list[Anchor]] = {m: [] for m, _, _ in windows}
        for a in data["anchors"]:
            anchors[a["measure"]].append(Anchor(time=a["time"], radius=a["radius"]))
        return cls(windows=windows, anchors=anchors)


class RhythmMeasurer:
    """녹음 오디오 + 박자 앵커(RhythmSpec) → 마디별 박자 측정(MeasureReading).

    연주 onset 피크를 앵커와 최근접 매칭해 drift(평균 편차)·score(일관성)·
    onset_ratio(피크 밀도)를 내고 classify_rhythm 으로 상태를 정한다.
    offset_s 는 파이프라인 고정 지연 보정값 — 배치는 전역 중앙값(global_offset),
    실시간은 호출자가 초반 마디로 추정해 넘긴다.
    """

    domain = Domain.RHYTHM

    def __init__(self, detector: OnsetDetector | None = None) -> None:
        self.detector = detector or LibrosaOnsetDetector()

    def measure(self, audio_path: str, spec: RhythmSpec) -> list[MeasureReading]:
        env = self.detector.envelope_from_file(audio_path)
        offset = self.global_offset(env, spec)
        return self.readings(env, spec, offset)

    def readings(
        self, env: OnsetEnvelope, spec: RhythmSpec, offset_s: float = 0.0
    ) -> list[MeasureReading]:
        return [self.reading(env, spec, m, offset_s) for m, _, _ in spec.windows]

    def reading_for_window(
        self,
        samples,
        sr: int,
        start_s: float,
        spec: RhythmSpec,
        measure: int,
        offset_s: float = 0.0,
    ) -> MeasureReading:
        env = self.detector.envelope(samples, sr, t0=start_s)
        return self.reading(env, spec, measure, offset_s)

    def global_offset(self, env: OnsetEnvelope, spec: RhythmSpec) -> float:
        import numpy as np

        devs = []
        for measure_index in spec.anchors:
            devs.extend(self._window_devs(env, spec, measure_index))
        return float(np.median(devs)) if devs else 0.0

    def window_offset(
        self, env: OnsetEnvelope, spec: RhythmSpec, measure_index: int
    ) -> float | None:
        import numpy as np

        devs = self._window_devs(env, spec, measure_index)
        return float(np.median(devs)) if devs else None

    def reading(
        self, env: OnsetEnvelope, spec: RhythmSpec, measure_index: int, offset_s: float
    ) -> MeasureReading:
        import numpy as np

        anchors = spec.anchors.get(measure_index, [])
        window = next((w for w in spec.windows if w[0] == measure_index), None)
        if not anchors or window is None:
            return MeasureReading(
                measure_index=measure_index, state=GOOD, valid=False, meta={}
            )

        _, start, end = window
        mid = (start + end) / 2
        times = [a.time for a in anchors]
        norm = float(np.median(np.diff(times))) if len(times) > 1 else (end - start) / 2
        halves = [
            self._eval_half(
                [a for a in anchors if lo <= a.time < hi], env, (lo, hi), offset_s, norm
            )
            for lo, hi in ((start, mid), (mid, end))
        ]
        if not any(h["valid"] and h["matched"] for h in halves):
            return MeasureReading(
                measure_index=measure_index,
                state=GOOD,
                valid=False,
                meta={"halves": [h["state"] for h in halves]},
            )
        return self._aggregate(measure_index, halves)

    def _window_devs(
        self, env: OnsetEnvelope, spec: RhythmSpec, measure_index: int
    ) -> list[float]:
        devs = []
        for a in spec.anchors.get(measure_index, []):
            p = env.nearest_to(a.time, SEARCH_RADIUS_S)
            if p is not None:
                devs.append(p - a.time)
        return devs

    def _eval_half(
        self,
        anchors: list[Anchor],
        env: OnsetEnvelope,
        bounds: tuple[float, float],
        offset_s: float,
        norm: float,
    ) -> dict:
        import numpy as np

        if not anchors:
            return {"valid": False, "state": GOOD, "matched": 0}

        deviations = []
        for a in anchors:
            p = env.nearest_to(a.time + offset_s, a.radius)
            if p is not None:
                deviations.append(p - offset_s - a.time)

        lo, hi = bounds
        ratio = env.count_in(lo + offset_s, hi + offset_s) / len(anchors)
        if not deviations:
            return {
                "valid": True,
                "state": classify_rhythm(0.0, 0.0, ratio),
                "matched": 0,
                "drift_ms": 0.0,
                "score": 0.0,
                "onset_ratio": round(ratio, 3),
            }

        mean_drift = float(np.mean(deviations))
        rel = [abs(d - mean_drift) / norm for d in deviations]
        score = float(np.exp(-np.mean(rel) * 3))
        drift_ms = mean_drift * 1000
        return {
            "valid": True,
            "state": classify_rhythm(score, drift_ms, ratio),
            "matched": len(deviations),
            "drift_ms": round(drift_ms, 1),
            "score": round(score, 3),
            "onset_ratio": round(ratio, 3),
        }

    def _aggregate(self, measure_index: int, halves: list[dict]) -> MeasureReading:
        valid = [h for h in halves if h["valid"]]
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
