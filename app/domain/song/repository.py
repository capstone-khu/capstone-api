from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.song.model import Song, SongMeasure


class SongRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_songs(self) -> list[Song]:
        result = await self.session.execute(select(Song).order_by(Song.number))
        return list(result.scalars().all())

    async def get_by_id(self, song_id: int) -> Song | None:
        return await self.session.get(Song, song_id)

    async def list_measures(self, song_id: int) -> list[SongMeasure]:
        result = await self.session.execute(
            select(SongMeasure)
            .where(SongMeasure.song_id == song_id)
            .order_by(SongMeasure.measure_index)
        )
        return list(result.scalars().all())
