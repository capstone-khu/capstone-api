from pathlib import Path

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.common.media import save_upload
from app.domain.agent.realtime import store
from app.domain.agent.repository import AgentRepository
from app.domain.session.model import DuetVideo, Recording
from app.domain.session.repository import SessionRepository
from app.domain.session.schema import (
    DuetVideoResponse,
    Marking,
    MeasureMarkings,
    PreviousMarkingsResponse,
    SessionCompleteResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from app.domain.song.model import Song
from app.domain.song.repository import SongRepository
from app.domain.user.model import User


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
        self,
        user_id: int,
        session_id: int,
        audio: UploadFile,
        video: UploadFile,
        background: BackgroundTasks,
    ) -> SessionCompleteResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)
        if session.status in ("completed", "aborted"):
            raise BusinessException(ErrorCode.SESSION_ALREADY_ENDED)

        recording = Recording(
            session_id=session_id,
            user_id=user_id,
            song_id=session.song_id,
            audio_url="",
            video_url="",
        )
        self.session.add(recording)
        await self.session.flush()

        video_ext = Path(video.filename or "").suffix or ".webm"
        audio_ext = Path(audio.filename or "").suffix or ".webm"
        recording.video_url = await save_upload(
            video, f"recordings/{recording.id}{video_ext}"
        )
        recording.audio_url = await save_upload(
            audio, f"recordings/{recording.id}.audio{audio_ext}"
        )

        live = store.get(session_id)
        if live is not None:
            repo = AgentRepository(self.session)
            await repo.insert_feedback_events(session_id, live.outputs)
            await repo.upsert_q_values(user_id, live.changed_q())
            live.completed = True

        duet_id = None
        if session.mode == "duet" and session.partner_recording_id is not None:
            duet = DuetVideo(
                user_id=user_id,
                session_id=session_id,
                song_id=session.song_id,
                partner_recording_id=session.partner_recording_id,
                status="pending",
            )
            self.session.add(duet)
            await self.session.flush()
            duet_id = duet.id

        session.status = "completed"
        session.ended_at = func.now()
        await self.session.commit()

        if duet_id is not None:
            from app.domain.session.duet import synthesize

            background.add_task(synthesize, duet_id)

        return SessionCompleteResponse(
            session_id=session_id,
            recording_id=recording.id,
            duet_composite_id=duet_id,
        )

    async def previous_markings(
        self, user_id: int, session_id: int
    ) -> PreviousMarkingsResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)

        previous = await self.sessions.latest_completed(
            user_id, session.song_id, session_id
        )
        if previous is None:
            return PreviousMarkingsResponse(measures=[])

        rows = await AgentRepository(self.session).markings_for_session(previous.id)
        by_measure: dict[int, list[Marking]] = {}
        for row in rows:
            by_measure.setdefault(row.measure_index, []).append(
                Marking(
                    domain=row.domain, action_id=row.action_id, feedback=row.feedback
                )
            )
        measures = [
            MeasureMarkings(measure_index=measure, markings=markings)
            for measure, markings in sorted(by_measure.items())
        ]
        return PreviousMarkingsResponse(
            previous_session_id=previous.id, measures=measures
        )

    async def get_duet_video(
        self, user_id: int, duet_composite_id: int
    ) -> DuetVideoResponse:
        row = (
            await self.session.execute(
                select(DuetVideo, Song.title, User.name)
                .join(Song, Song.id == DuetVideo.song_id)
                .join(Recording, Recording.id == DuetVideo.partner_recording_id)
                .join(User, User.id == Recording.user_id)
                .where(DuetVideo.id == duet_composite_id)
            )
        ).first()
        if row is None:
            raise BusinessException(ErrorCode.DUET_NOT_FOUND)
        duet, song_title, partner_name = row
        if duet.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_DUET)
        return DuetVideoResponse(
            duet_composite_id=duet.id,
            song_title=song_title,
            partner_name=partner_name,
            status=duet.status,
            composite_video_url=duet.composite_video_url,
            created_at=duet.created_at,
        )

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
