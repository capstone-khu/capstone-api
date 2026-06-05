import asyncio

from sqlalchemy import select

from app.common.media import media_path
from app.common.persistence import AsyncSessionLocal
from app.domain.session.model import DuetVideo, Recording

_FILTER = (
    "[0:v]scale=-2:480[a];[1:v]scale=-2:480[b];"
    "[a][b]hstack=inputs=2[v];"
    "[0:a][1:a]amix=inputs=2:duration=longest[au]"
)


async def synthesize(duet_id: int) -> None:
    """협주 좌우 분할 합성(BackgroundTasks). 내 녹화 + 상대 녹화 → /media/duet."""
    async with AsyncSessionLocal() as db:
        duet = await db.get(DuetVideo, duet_id)
        if duet is None:
            return
        mine = (
            await db.execute(
                select(Recording)
                .where(Recording.session_id == duet.session_id)
                .order_by(Recording.id.desc())
                .limit(1)
            )
        ).scalars().first()
        partner = await db.get(Recording, duet.partner_recording_id)
        if mine is None or partner is None:
            duet.status = "failed"
            await db.commit()
            return

        duet.status = "processing"
        await db.commit()

        out_rel = f"duet/{duet_id}.mp4"
        out_path = media_path(f"/media/{out_rel}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ok = await _run_ffmpeg(
            media_path(mine.video_url), media_path(partner.video_url), out_path
        )

        duet.status = "ready" if ok else "failed"
        if ok:
            duet.composite_video_url = f"/media/{out_rel}"
        await db.commit()


async def _run_ffmpeg(left, right, out) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", str(left), "-i", str(right),
            "-filter_complex", _FILTER,
            "-map", "[v]", "-map", "[au]",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(out),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return proc.returncode == 0 and out.exists()
    except (FileNotFoundError, OSError):
        return False
