import shutil
from pathlib import Path

from fastapi import UploadFile

from app.common.config import settings

SEED_MEDIA: dict[str, str] = {
    "seeds/media/twinkle_twinkle.piano.mp4": "recordings/1.mp4",
}


async def save_upload(upload: UploadFile, target_rel: str) -> str:
    """업로드 파일을 media 볼륨에 저장하고 `/media/...` URL 을 반환한다."""
    destination = Path(settings.MEDIA_ROOT) / target_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as out:
        while chunk := await upload.read(1024 * 1024):
            out.write(chunk)
    return f"/media/{target_rel}"


def media_path(url: str) -> Path:
    """`/media/...` URL 을 실제 파일 경로로 변환한다."""
    return Path(settings.MEDIA_ROOT) / url.removeprefix("/media/")


def sync_seed_media() -> None:
    media_root = Path(settings.MEDIA_ROOT)
    for source, target in SEED_MEDIA.items():
        destination = media_root / target
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)
