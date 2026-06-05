from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.domain.agent.realtime import store
from app.domain.agent.repository import AgentRepository
from app.domain.session.repository import SessionRepository
from app.domain.session.schema import (
    SessionCompleteResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from app.domain.song.repository import SongRepository


class SessionService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = SessionRepository(session)
        self.songs = SongRepository(session)

    async def create_session(
        self, user_id: int, request: SessionCreateRequest
    ) -> SessionCreateResponse:
        song = await self.songs.get_by_id(request.song_id)
        if song is None:
            raise BusinessException(ErrorCode.SONG_NOT_FOUND)

        partner_name = None
        audio_url = None
        if request.mode == "duet":
            found = await self.sessions.get_recording_with_partner(
                request.partner_recording_id
            )
            if found is None:
                raise BusinessException(ErrorCode.RECORDING_NOT_FOUND)
            recording, name = found
            if recording.song_id != request.song_id or recording.user_id == user_id:
                raise BusinessException(ErrorCode.INVALID_DUET_PARTNER)
            partner_name = name
            audio_url = recording.audio_url

        session = await self.sessions.create(
            user_id=user_id,
            song_id=request.song_id,
            mode=request.mode,
            partner_recording_id=request.partner_recording_id,
        )
        await self.session.commit()

        return SessionCreateResponse(
            session_id=session.id,
            status=session.status,
            song_title=song.title,
            partner_name=partner_name,
            audio_url=audio_url,
        )

    async def complete_session(
        self, user_id: int, session_id: int
    ) -> SessionCompleteResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)
        if session.status in ("completed", "aborted"):
            raise BusinessException(ErrorCode.SESSION_ALREADY_ENDED)

        live = store.get(session_id)
        if live is not None:
            repo = AgentRepository(self.session)
            await repo.insert_feedback_events(session_id, live.outputs)
            await repo.upsert_q_values(user_id, live.changed_q())
            live.completed = True

        session.status = "completed"
        session.ended_at = func.now()
        await self.session.commit()
        return SessionCompleteResponse(session_id=session_id)

    async def abort_session(self, user_id: int, session_id: int) -> None:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)
        if session.status in ("completed", "aborted"):
            raise BusinessException(ErrorCode.SESSION_ALREADY_ENDED)

        session.status = "aborted"
        session.ended_at = func.now()
        await self.session.commit()
