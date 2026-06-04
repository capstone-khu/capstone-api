from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.song.model import Song


class SongRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_songs(self) -> list[Song]:
        result = await self.session.execute(select(Song).order_by(Song.number))
        return list(result.scalars().all())
