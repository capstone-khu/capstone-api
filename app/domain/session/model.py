from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.persistence import BaseEntity


class Session(BaseEntity):
    __tablename__ = "sessions"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    song_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("songs.id"))
    mode: Mapped[str] = mapped_column(Enum("solo", "duet", name="session_mode"))
    partner_recording_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("recordings.id", use_alter=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum("created", "in_progress", "completed", "aborted", name="session_status")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Recording(BaseEntity):
    __tablename__ = "recordings"

    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    song_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("songs.id"))
    audio_url: Mapped[str] = mapped_column(String(500))
    video_url: Mapped[str] = mapped_column(String(500))
    available_for_duet: Mapped[bool] = mapped_column(
        Boolean, server_default=text("1")
    )


class DuetVideo(BaseEntity):
    __tablename__ = "duet_videos"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id"))
    song_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("songs.id"))
    partner_recording_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recordings.id")
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="duet_status")
    )
    composite_video_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
