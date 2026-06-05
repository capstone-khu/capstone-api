from app.domain.agent.pitch.policy import classify_cents
from app.domain.agent.schema import Domain, MeasureReading
from app.domain.agent.score import Score

SAMPLE_RATE = 48000
FRAME_MS = 50
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000
CONF_THRESHOLD = 0.5
MIN_VALID_FRAMES = 5


class PitchMeasurer:
    """녹음 오디오 + 시간축 score → 마디별 음정 측정(MeasureReading).

    SwiftF0·librosa·noisereduce·numpy 는 무거우므로 measure() 안에서 lazy import.
    프로토타입 realtime_bridge 의 프레임 루프를 파일 배치로 옮긴 것(마이크·스레드 제거).
    """

    domain = Domain.PITCH

    def measure(self, audio_path: str, score: Score) -> list[MeasureReading]:
        import librosa
        from swift_f0 import core

        y, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
        model = core.SwiftF0()
        cents_by_measure = self.accumulate_cents(y, score, model)
        return self._aggregate(score, cents_by_measure)

    def accumulate_cents(
        self, y, score: Score, model, time_offset: float = 0.0
    ) -> dict[int, list[float]]:
        import noisereduce as nr
        import numpy as np

        cents_by_measure: dict[int, list[float]] = {}
        prev_f0 = 0.0

        for i in range(0, len(y) - FRAME_SIZE, FRAME_SIZE):
            timestamp = time_offset + i / float(SAMPLE_RATE)
            target = score.target_at(timestamp)
            if target is None or target.get("measure") is None:
                continue

            chunk = y[i : i + FRAME_SIZE].astype(np.float32)
            denoised = nr.reduce_noise(
                y=chunk, sr=SAMPLE_RATE, prop_decrease=0.9, stationary=True
            )
            res = model.detect_from_array(denoised, sample_rate=SAMPLE_RATE)
            if len(res.pitch_hz) == 0:
                continue

            actual_hz = float(np.median(res.pitch_hz))
            confidence = float(np.median(res.confidence))
            if prev_f0 > 0 and abs(actual_hz - prev_f0 * 2) < prev_f0 * 0.1:
                actual_hz /= 2
            if actual_hz > 1100:
                actual_hz /= 2
            prev_f0 = actual_hz

            if confidence < CONF_THRESHOLD or actual_hz <= 0:
                continue
            cents = score.cents_at(actual_hz, timestamp)
            if cents is None:
                continue

            cents_by_measure.setdefault(target["measure"], []).append(cents)

        return cents_by_measure

    def reading_for_window(
        self, samples, start_s: float, score: Score, measure: int, model
    ) -> MeasureReading:
        from statistics import fmean

        cents_by_measure = self.accumulate_cents(samples, score, model, start_s)
        cents_list = cents_by_measure.get(measure, [])
        if len(cents_list) < MIN_VALID_FRAMES:
            return MeasureReading(
                measure_index=measure,
                state=classify_cents(0.0),
                valid=False,
                meta={"frames": len(cents_list)},
            )

        avg_cents = fmean(cents_list)
        return MeasureReading(
            measure_index=measure,
            state=classify_cents(avg_cents),
            valid=True,
            meta={"avg_cents": round(avg_cents, 1), "frames": len(cents_list)},
        )

    def _aggregate(
        self, score: Score, cents_by_measure: dict[int, list[float]]
    ) -> list[MeasureReading]:
        from statistics import fmean

        readings: list[MeasureReading] = []
        for measure in score.measures():
            cents_list = cents_by_measure.get(measure, [])
            if len(cents_list) < MIN_VALID_FRAMES:
                readings.append(
                    MeasureReading(
                        measure_index=measure,
                        state=classify_cents(0.0),
                        valid=False,
                        meta={"frames": len(cents_list)},
                    )
                )
                continue

            avg_cents = fmean(cents_list)
            readings.append(
                MeasureReading(
                    measure_index=measure,
                    state=classify_cents(avg_cents),
                    valid=True,
                    meta={"avg_cents": round(avg_cents, 1), "frames": len(cents_list)},
                )
            )
        return readings
