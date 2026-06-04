from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.domain.song.repository import SongRepository
from app.domain.song.schema import (
    DuetPartner,
    DuetPartnersResponse,
    Note,
    ScoreMeasure,
    ScoreResponse,
    SongDetail,
    SongListResponse,
    SongSummary,
)


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

    async def get_score(self, song_id: int) -> ScoreResponse:
        song = await self.songs.get_by_id(song_id)
        if song is None:
            raise BusinessException(ErrorCode.SONG_NOT_FOUND)

        measures = await self.songs.list_measures(song_id)
        return ScoreResponse(
            song=SongDetail(
                id=song.id,
                number=song.number,
                title=song.title,
                bpm=song.bpm,
                time_signature=song.time_signature,
                total_measures=song.total_measures,
            ),
            measures=[
                ScoreMeasure(
                    measure_index=measure.measure_index,
                    notes=[Note(**note) for note in measure.notes],
                )
                for measure in measures
            ],
        )

    async def list_duet_partners(
        self, song_id: int, exclude_user_id: int
    ) -> DuetPartnersResponse:
        song = await self.songs.get_by_id(song_id)
        if song is None:
            raise BusinessException(ErrorCode.SONG_NOT_FOUND)

        partners = await self.songs.list_duet_partners(song_id, exclude_user_id)
        return DuetPartnersResponse(
            partners=[
                DuetPartner(
                    recording_id=recording.id,
                    user_name=user_name,
                    song_title=song.title,
                    recorded_at=recording.created_at,
                )
                for recording, user_name in partners
            ]
        )
