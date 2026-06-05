from app.domain.agent.pitch.measurer import SAMPLE_RATE, PitchMeasurer
from app.domain.agent.posture.measurer import PoseMeasurer, PostureSpec
from app.domain.agent.posture.policy import classify_posture
from app.domain.agent.rhythm.measurer import RhythmMeasurer, RhythmSpec
from app.domain.agent.schema import Domain, MeasureReading
from app.domain.agent.score import Score, load_timed_score

GOOD = "GOOD"


def _invalid(measure_index: int) -> MeasureReading:
    return MeasureReading(measure_index=measure_index, state=GOOD, valid=False, meta={})


class _AudioBuffer:
    """ts 태깅된 PCM16 청크를 모아 마디 윈도우 구간을 float32 로 잘라준다."""

    def __init__(self) -> None:
        self._chunks: list[tuple[int, object]] = []
        self._np = None

    def feed(self, ts_ms: int, payload: bytes) -> None:
        import numpy as np

        self._np = np
        samples = np.frombuffer(payload, dtype="<i2").astype(np.float32) / 32768.0
        self._chunks.append((ts_ms, samples))

    def segment(self, start_s: float, end_s: float, sr: int):
        if not self._chunks:
            return None
        np = self._np
        base_s = self._chunks[0][0] / 1000.0
        audio = np.concatenate([c for _, c in self._chunks])
        i0 = max(0, int((start_s - base_s) * sr))
        i1 = min(len(audio), int((end_s - base_s) * sr))
        if i1 <= i0:
            return None
        return audio[i0:i1]


class PitchAggregator:
    domain = Domain.PITCH

    def __init__(self, score: Score, windows: list[tuple[int, float, float]]) -> None:
        self.score = score
        self.windows = {m: (s, e) for m, s, e in windows}
        self.measurer = PitchMeasurer()
        self.buffer = _AudioBuffer()
        self._model = None

    def feed(self, ts_ms: int, payload: bytes) -> None:
        self.buffer.feed(ts_ms, payload)

    def reading(self, measure_index: int) -> MeasureReading:
        start, end = self.windows[measure_index]
        seg = self.buffer.segment(start, end, SAMPLE_RATE)
        if seg is None or len(seg) == 0:
            return _invalid(measure_index)
        if self._model is None:
            from swift_f0 import core

            self._model = core.SwiftF0()
        return self.measurer.reading_for_window(
            seg, start, self.score, measure_index, self._model
        )


class RhythmAggregator:
    domain = Domain.RHYTHM

    def __init__(
        self, spec: RhythmSpec, windows: list[tuple[int, float, float]]
    ) -> None:
        self.spec = spec
        self.windows = {m: (s, e) for m, s, e in windows}
        self.measurer = RhythmMeasurer()
        self.buffer = _AudioBuffer()

    def feed(self, ts_ms: int, payload: bytes) -> None:
        self.buffer.feed(ts_ms, payload)

    def reading(self, measure_index: int) -> MeasureReading:
        start, end = self.windows[measure_index]
        seg = self.buffer.segment(start, end, SAMPLE_RATE)
        if seg is None or len(seg) == 0:
            return _invalid(measure_index)
        return self.measurer.reading_for_window(
            seg, SAMPLE_RATE, start, self.spec, measure_index
        )


class PostureAggregator:
    domain = Domain.POSTURE

    def __init__(self, spec: PostureSpec) -> None:
        self.spec = spec
        self.measurer = PoseMeasurer()
        self.sequences: dict[int, list] = {m: [] for m, _, _ in spec.windows}
        self._landmarker = None
        self._analyzer = None
        self._mp = None
        self._np = None
        self._prev_wrist = None
        self._last_ts = -1

    def feed(self, ts_ms: int, payload: bytes) -> None:
        import cv2

        self._ensure()
        if int(ts_ms) <= self._last_ts:
            return
        self._last_ts = int(ts_ms)

        arr = self._np.frombuffer(payload, dtype=self._np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, int(ts_ms))

        landmarks = self.measurer._landmarks(result)
        vector, self._prev_wrist = self.measurer._features(landmarks, self._prev_wrist)
        measure = self.measurer._window_for(ts_ms / 1000.0, self.spec.windows)
        if measure is not None and vector is not None:
            self.sequences[measure].append(vector)

    def reading(self, measure_index: int) -> MeasureReading:
        seq = self.sequences.get(measure_index, [])
        if len(seq) < 2:
            return _invalid(measure_index)
        result = self._analyzer.analyze(self._np.array(seq, dtype=self._np.float32))
        return MeasureReading(
            measure_index=measure_index,
            state=classify_posture(result["stable"], result["top_feature_index"]),
            valid=True,
            meta={
                "case": result["case"],
                "final_score": result["final_score"],
                "top_feature": result["top_feature_index"],
            },
        )

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def _ensure(self) -> None:
        if self._landmarker is not None:
            return
        import mediapipe as mp
        import numpy as np

        from app.domain.agent.posture.analyzer import PostureAnalyzer

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=self.spec.task_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self._analyzer = PostureAnalyzer(self.spec.pkl_path)
        self._mp = mp
        self._np = np


async def build_live_session(db, session_obj):
    """세션 정보로 3 도메인 집계기·엔진(Q 메모리 로드)을 구성한다."""
    from app.domain.agent.pitch.policy import PitchPolicy
    from app.domain.agent.posture.policy import PosturePolicy
    from app.domain.agent.qlearning import QLearningEngine
    from app.domain.agent.realtime.runtime import LiveSession
    from app.domain.agent.repository import AgentRepository
    from app.domain.agent.rhythm.policy import RhythmPolicy
    from app.domain.song.model import Song

    song_id = session_obj.song_id
    score = load_timed_score(song_id)
    windows = score.measure_windows()

    song = await db.get(Song, song_id)
    if song is None:
        raise ValueError(f"존재하지 않는 곡입니다: song_id={song_id}")
    beats_per_measure = int(song.time_signature.split("/")[0])
    rhythm_spec = RhythmSpec(
        bpm=song.bpm,
        beats_per_measure=beats_per_measure,
        total_measures=song.total_measures,
    )
    posture_spec = PostureSpec(windows=windows)

    entries = await AgentRepository(db).load_q_table(session_obj.user_id)

    def slice_q(domain: Domain) -> dict[tuple[str, str], list[float]]:
        return {
            (e.state, e.action): [e.q_value, e.update_count]
            for e in entries
            if e.domain == domain.value
        }

    engines = {
        Domain.PITCH: QLearningEngine(PitchPolicy(), slice_q(Domain.PITCH)),
        Domain.RHYTHM: QLearningEngine(RhythmPolicy(), slice_q(Domain.RHYTHM)),
        Domain.POSTURE: QLearningEngine(PosturePolicy(), slice_q(Domain.POSTURE)),
    }
    aggregators = {
        Domain.PITCH: PitchAggregator(score, windows),
        Domain.RHYTHM: RhythmAggregator(rhythm_spec, windows),
        Domain.POSTURE: PostureAggregator(posture_spec),
    }
    return LiveSession(
        session_id=session_obj.id,
        user_id=session_obj.user_id,
        song_id=song_id,
        windows=windows,
        engines=engines,
        aggregators=aggregators,
    )
