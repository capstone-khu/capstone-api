from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.persistence import BaseEntity


class Song(BaseEntity):
    __tablename__ = "songs"

    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(100))
    bpm: Mapped[int] = mapped_column(Integer)
    time_signature: Mapped[str] = mapped_column(String(10))
    total_measures: Mapped[int] = mapped_column(Integer)


class SongMeasure(BaseEntity):
    __tablename__ = "song_measures"
    __table_args__ = (UniqueConstraint("song_id", "measure_index"),)

    song_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("songs.id"))
    measure_index: Mapped[int] = mapped_column(Integer)
    notes: Mapped[list[dict]] = mapped_column(JSON)
