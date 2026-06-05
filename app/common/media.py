import shutil
from pathlib import Path

from app.common.config import settings

SEED_MEDIA: dict[str, str] = {
    "seeds/media/twinkle_twinkle.piano.mp4": "recordings/1.mp4",
}


def sync_seed_media() -> None:
    media_root = Path(settings.MEDIA_ROOT)
    for source, target in SEED_MEDIA.items():
        destination = media_root / target
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)
