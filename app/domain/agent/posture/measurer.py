import math
from dataclasses import dataclass

from app.domain.agent.posture.analyzer import PostureAnalyzer
from app.domain.agent.posture.policy import GOOD, classify_posture
from app.domain.agent.schema import Domain, MeasureReading

PRESENCE_THRESHOLD = 0.5
DEFAULT_TASK_PATH = "fixtures/models/pose_landmarker_lite.task"
DEFAULT_PKL_PATH = "fixtures/models/pose_model.pkl"


@dataclass
class PostureSpec:
    windows: list[tuple[int, float, float]]
    task_path: str = DEFAULT_TASK_PATH
    pkl_path: str = DEFAULT_PKL_PATH


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle(a, b, c) -> float | None:
    abx, aby = a[0] - b[0], a[1] - b[1]
    cbx, cby = c[0] - b[0], c[1] - b[1]
    nab, ncb = math.hypot(abx, aby), math.hypot(cbx, cby)
    if nab == 0 or ncb == 0:
        return None
    cos = max(-1.0, min(1.0, (abx * cbx + aby * cby) / (nab * ncb)))
    return math.degrees(math.acos(cos))


class PoseMeasurer:
    """녹화 영상 + 마디 윈도우 → 마디별 자세 측정(MeasureReading).

    프로토타입(pose-agent)을 옮긴 것 — MediaPipe PoseLandmarker(VIDEO 모드)로 마디 구간
    프레임의 6 feature 시퀀스를 모아 PostureAnalyzer 로 분석한다. 무거운 측정 deps
    (cv2·mediapipe·numpy)는 measure() 안에서 lazy import.
    """

    domain = Domain.POSTURE

    def measure(self, video_path: str, spec: PostureSpec) -> list[MeasureReading]:
        import cv2
        import mediapipe as mp
        import numpy as np

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=spec.task_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
        )
        analyzer = PostureAnalyzer(spec.pkl_path)
        capture = cv2.VideoCapture(video_path)
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0

        sequences: dict[int, list] = {m: [] for (m, _, _) in spec.windows}
        prev_wrist = None
        frame_index = 0
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while capture.isOpened():
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp = frame_index / fps
                frame_index += 1
                measure = self._window_for(timestamp, spec.windows)
                if measure is None:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(image, int(timestamp * 1000))
                landmarks = self._landmarks(result)
                vector, prev_wrist = self._features(landmarks, prev_wrist)
                if vector is not None:
                    sequences[measure].append(vector)
        capture.release()

        readings: list[MeasureReading] = []
        for m, _, _ in spec.windows:
            seq = sequences[m]
            if len(seq) < 2:
                readings.append(
                    MeasureReading(measure_index=m, state=GOOD, valid=False, meta={})
                )
                continue
            result = analyzer.analyze(np.array(seq, dtype=np.float32))
            readings.append(
                MeasureReading(
                    measure_index=m,
                    state=classify_posture(
                        result["stable"], result["top_feature_index"]
                    ),
                    valid=True,
                    meta={
                        "case": result["case"],
                        "final_score": result["final_score"],
                        "top_feature": result["top_feature_index"],
                    },
                )
            )
        return readings

    def _window_for(self, timestamp: float, windows) -> int | None:
        for m, start, end in windows:
            if start <= timestamp < end:
                return m
        return None

    def _landmarks(self, result) -> dict | None:
        if not result.pose_landmarks:
            return None
        return {
            i: (lm.x, lm.y)
            for i, lm in enumerate(result.pose_landmarks[0])
            if lm.presence >= PRESENCE_THRESHOLD
        }

    def _features(self, landmarks: dict | None, prev_wrist):
        if not landmarks:
            return None, prev_wrist

        def at(i):
            return landmarks.get(i)

        wrist_shoulder = _dist(at(15), at(11)) if at(15) and at(11) else 0.0
        shoulder_diff = abs(at(11)[1] - at(12)[1]) if at(11) and at(12) else 0.0
        wrist = at(15)
        velocity = _dist(wrist, prev_wrist) if wrist and prev_wrist else 0.0
        left_elbow = (
            _angle(at(11), at(13), at(15)) if at(11) and at(13) and at(15) else 0.0
        )
        right_elbow = (
            _angle(at(12), at(14), at(16)) if at(12) and at(14) and at(16) else 0.0
        )
        right_wrist = (
            _angle(at(14), at(16), at(18)) if at(14) and at(16) and at(18) else 0.0
        )

        vector = [
            wrist_shoulder or 0.0,
            shoulder_diff or 0.0,
            velocity or 0.0,
            left_elbow or 0.0,
            right_elbow or 0.0,
            right_wrist or 0.0,
        ]
        return vector, (wrist or prev_wrist)
