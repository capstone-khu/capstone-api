import logging

logger = logging.getLogger(__name__)


def warm_blocking() -> None:
    """실시간 측정 스택(import·numba JIT·MediaPipe GL)을 부팅 후 1회 미리 데운다.

    콜드 스타트(첫 WS 세션 첫 마디 ~60s)를 배포 직후로 흡수한다. 측정 deps 가 없는
    환경(로컬 dev 등)에선 각 블록이 조용히 skip 된다. 백그라운드 실행 전제(논블로킹).
    """
    import numpy as np

    try:
        import noisereduce as nr

        from app.domain.agent.pitch.measurer import get_swift_f0

        dummy = np.zeros(4096, dtype=np.float32)
        get_swift_f0().detect_from_array(dummy, sample_rate=48000)
        nr.reduce_noise(y=dummy, sr=48000, prop_decrease=0.9, stationary=True)
    except Exception as exc:
        logger.warning("음정 워밍업 skip: %s", exc)

    try:
        import librosa

        librosa.beat.beat_track(y=np.zeros(48000, dtype=np.float32), sr=48000)
    except Exception as exc:
        logger.warning("박자 워밍업 skip: %s", exc)

    try:
        import cv2  # noqa: F401
        import mediapipe as mp

        from app.domain.agent.posture.analyzer import PostureAnalyzer
        from app.domain.agent.posture.measurer import DEFAULT_TASK_PATH

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=DEFAULT_TASK_PATH),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
        )
        landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        landmarker.detect_for_video(image, 0)
        landmarker.close()
        PostureAnalyzer()
    except Exception as exc:
        logger.warning("자세 워밍업 skip: %s", exc)

    logger.info("실시간 측정 스택 워밍업 완료")
