from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.session.model import Recording
from app.domain.song.model import Song, SongMeasure
from app.domain.user.model import User


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

    async def get_measure(self, song_id: int, measure_index: int) -> SongMeasure | None:
        result = await self.session.execute(
            select(SongMeasure).where(
                SongMeasure.song_id == song_id,
                SongMeasure.measure_index == measure_index,
            )
        )
        return result.scalars().first()

    async def list_duet_partners(
        self, song_id: int, exclude_user_id: int
    ) -> list[tuple[Recording, str]]:
        result = await self.session.execute(
            select(Recording, User.name)
            .join(User, User.id == Recording.user_id)
            .where(
                Recording.song_id == song_id,
                Recording.available_for_duet.is_(True),
                Recording.user_id != exclude_user_id,
            )
            .order_by(Recording.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]
