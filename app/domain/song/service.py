from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.song.repository import SongRepository
from app.domain.song.schema import SongListResponse, SongSummary


class SongService:

    def __init__(self, session: AsyncSession) -> None:
        self.songs = SongRepository(session)

    async def list_songs(self) -> SongListResponse:
        songs = await self.songs.list_songs()
        return SongListResponse(
            total=len(songs),
            songs=[
                SongSummary(id=song.id, number=song.number, title=song.title)
                for song in songs
            ],
        )
