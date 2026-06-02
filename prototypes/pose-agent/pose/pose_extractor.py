import cv2
from pathlib import Path
import mediapipe as mp

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3),
    (0, 4), (4, 5), (5, 6),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "pose_landmarker_lite.task"

class PoseExtractor:
    def __init__(self, source, model_path=None, presence_threshold=0.5):
        self.source = source
        self.presence_threshold = presence_threshold
        self.latest_result = None
        self.timestamp = 0
        self.model_path = self._resolve_model_path(model_path)
        self.model_asset_buffer = self.model_path.read_bytes()

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=self.model_asset_buffer),
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._on_result,
        )
        self.landmarker = PoseLandmarker.create_from_options(options)

    def _resolve_model_path(self, model_path):
        path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not path.is_absolute():
            candidates = [
                Path.cwd() / path,
                PROJECT_ROOT / path,
            ]
            path = next((candidate for candidate in candidates if candidate.exists()), path)

        if not path.exists():
            raise FileNotFoundError(
                f"Pose landmarker model not found: {path}. "
                f"Expected default model at: {DEFAULT_MODEL_PATH}"
            )

        return path

    def _on_result(self, result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        self.latest_result = result

    def extract(self, frame, draw=True):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        self.timestamp += 1
        self.landmarker.detect_async(mp_image, self.timestamp)

        landmarks = self.get_landmarks()
        annotated_frame = self.draw(frame, landmarks) if draw else frame

        return landmarks, annotated_frame

    def get_landmarks(self):
        if not self.latest_result or not self.latest_result.pose_landmarks:
            return None

        landmarks = self.latest_result.pose_landmarks[0]
        return {
            idx: landmark
            for idx, landmark in enumerate(landmarks)
            if landmark.presence >= self.presence_threshold
        }

    def draw(self, frame, landmarks):
        if not landmarks:
            return frame

        height, width = frame.shape[:2]
        points = {}

        for idx, landmark in landmarks.items():
            cx = int(landmark.x * width)
            cy = int(landmark.y * height)
            points[idx] = (cx, cy)

            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
            cv2.putText(
                frame,
                str(idx),
                (cx + 6, cy - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 0),
                1,
            )

        for a, b in CONNECTIONS:
            if a in points and b in points:
                cv2.line(frame, points[a], points[b], (0, 180, 255), 2)

        return frame

    def release(self):
        self.landmarker.close()

    def run(self, frame_source=None, callback=None, display=True):
        if frame_source is None:
            frame_source = self.source

        try:
            while frame_source.isOpened():
                ret, frame = frame_source.read()
                if not ret:
                    break

                self.timestamp += 1
                landmarks, annotated_frame = self.extract(frame)

                if callback:
                    callback(landmarks)

                if display:
                    cv2.imshow("PoseExtractor", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

        finally:
            self.release()
