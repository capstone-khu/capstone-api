from pathlib import Path

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.common.media import save_upload
from app.domain.agent.realtime import store
from app.domain.agent.repository import AgentRepository
from app.domain.session import coach
from app.domain.session.model import AnalysisReport, DuetVideo, Recording
from app.domain.session.repository import SessionRepository
from app.domain.session.schema import (
    AnalysisDomains,
    DuetVideoResponse,
    Marking,
    MeasureDetailResponse,
    MeasureMarkings,
    MeasureResult,
    NoteItem,
    PreviousMarkingsResponse,
    SessionAnalysisResponse,
    SessionCompleteResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResultResponse,
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

    async def get_session_result(
        self, user_id: int, session_id: int
    ) -> SessionResultResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)
        if session.status != "completed":
            raise BusinessException(ErrorCode.SESSION_NOT_COMPLETED)

        song = await self.songs.get_by_id(session.song_id)

        agent_repo = AgentRepository(self.session)
        current_rows = await agent_repo.markings_for_session(session_id)

        previous = await self.sessions.latest_completed(
            user_id, session.song_id, session_id
        )
        previous_rows = (
            await agent_repo.markings_for_session(previous.id)
            if previous is not None
            else []
        )

        partner_name = None
        if session.mode == "duet" and session.partner_recording_id is not None:
            found = await self.sessions.get_recording_with_partner(
                session.partner_recording_id
            )
            if found is not None:
                _, partner_name = found

        current_by_measure: dict[int, list[Marking]] = {}
        for row in current_rows:
            current_by_measure.setdefault(row.measure_index, []).append(
                Marking(
                    domain=row.domain,
                    action_id=row.action_id,
                    feedback=row.feedback,
                )
            )

        previous_by_measure: dict[int, list[Marking]] = {}
        for row in previous_rows:
            previous_by_measure.setdefault(row.measure_index, []).append(
                Marking(
                    domain=row.domain,
                    action_id=row.action_id,
                    feedback=row.feedback,
                )
            )

        all_measures = sorted(set(current_by_measure) | set(previous_by_measure))
        measures = [
            MeasureResult(
                measure_index=m,
                current=current_by_measure.get(m, []),
                previous=previous_by_measure.get(m, []),
            )
            for m in all_measures
        ]

        return SessionResultResponse(
            session_id=session_id,
            song_id=session.song_id,
            song_title=song.title,
            played_at=session.ended_at,
            mode=session.mode,
            partner_name=partner_name,
            measures=measures,
        )

    async def get_measure_detail(
        self, user_id: int, session_id: int, measure_index: int
    ) -> MeasureDetailResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)

        measure = await self.songs.get_measure(session.song_id, measure_index)
        if measure is None:
            raise BusinessException(ErrorCode.MEASURE_NOT_FOUND)
        notes = [NoteItem(**n) for n in measure.notes]

        agent_repo = AgentRepository(self.session)
        current_rows = await agent_repo.markings_for_measure(session_id, measure_index)
        current_markings = [
            Marking(domain=r.domain, action_id=r.action_id, feedback=r.feedback)
            for r in current_rows
        ]

        previous = await self.sessions.latest_completed(
            user_id, session.song_id, session_id
        )
        previous_markings = []
        if previous is not None:
            prev_rows = await agent_repo.markings_for_measure(
                previous.id, measure_index
            )
            previous_markings = [
                Marking(domain=r.domain, action_id=r.action_id, feedback=r.feedback)
                for r in prev_rows
            ]

        return MeasureDetailResponse(
            measure_index=measure_index,
            notes=notes,
            current_markings=current_markings,
            previous_markings=previous_markings,
        )

    async def get_session_analysis(
        self, user_id: int, session_id: int
    ) -> SessionAnalysisResponse:
        session = await self.sessions.get_by_id(session_id)
        if session is None:
            raise BusinessException(ErrorCode.SESSION_NOT_FOUND)
        if session.user_id != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN_SESSION)
        if session.status != "completed":
            raise BusinessException(ErrorCode.SESSION_NOT_COMPLETED)

        agent_repo = AgentRepository(self.session)
        focus_measures = await agent_repo.focus_measures(session_id)

        report = await self.sessions.get_analysis_report(session_id)
        if report is None:
            song = await self.songs.get_by_id(session.song_id)
            events = await agent_repo.events_for_session(session_id)
            previous = await self.sessions.latest_completed(
                user_id, session.song_id, session_id
            )
            previous_events = (
                await agent_repo.markings_for_session(previous.id)
                if previous is not None
                else []
            )

            result = await coach.generate(song.title, events, previous_events)
            if result is None:
                raise BusinessException(ErrorCode.ANALYSIS_GENERATION_FAILED)

            report = AnalysisReport(
                session_id=session_id,
                headline=result.headline,
                coach_comment=result.coach_comment,
                domains={
                    "pitch": result.pitch.model_dump(exclude_none=True),
                    "rhythm": result.rhythm.model_dump(exclude_none=True),
                    "posture": result.posture.model_dump(exclude_none=True),
                },
            )
            self.session.add(report)
            await self.session.commit()

        return SessionAnalysisResponse(
            session_id=session_id,
            headline=report.headline,
            coach_comment=report.coach_comment,
            domains=AnalysisDomains(**report.domains),
            focus_measures=focus_measures,
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
