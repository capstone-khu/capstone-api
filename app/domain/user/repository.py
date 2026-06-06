from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent.model import FeedbackEvent
from app.domain.session.model import DuetVideo, Session
from app.domain.song.model import Song
from app.domain.user.model import User


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_name(self, name: str) -> User | None:
        result = await self.session.execute(select(User).where(User.name == name))
        return result.scalar_one_or_none()

    async def count_completed_sessions(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Session)
            .where(Session.user_id == user_id, Session.status == "completed")
        )
        return result.scalar_one()

    async def completed_sessions_page(
        self, user_id: int, offset: int, limit: int
    ) -> list[tuple[Session, str]]:
        result = await self.session.execute(
            select(Session, Song.title)
            .join(Song, Song.id == Session.song_id)
            .where(Session.user_id == user_id, Session.status == "completed")
            .order_by(Session.ended_at.desc(), Session.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def problem_counts(
        self, session_ids: list[int]
    ) -> dict[int, dict[str, int]]:
        result = await self.session.execute(
            select(
                FeedbackEvent.session_id,
                FeedbackEvent.domain,
                func.count(),
            )
            .where(
                FeedbackEvent.session_id.in_(session_ids),
                FeedbackEvent.state != "GOOD",
            )
            .group_by(FeedbackEvent.session_id, FeedbackEvent.domain)
        )
        counts: dict[int, dict[str, int]] = {}
        for session_id, domain, count in result.all():
            counts.setdefault(session_id, {})[domain] = count
        return counts

    async def focus_measures_by_session(
        self, session_ids: list[int]
    ) -> dict[int, list[int]]:
        result = await self.session.execute(
            select(FeedbackEvent.session_id, FeedbackEvent.measure_index)
            .where(
                FeedbackEvent.session_id.in_(session_ids),
                FeedbackEvent.state != "GOOD",
            )
            .group_by(FeedbackEvent.session_id, FeedbackEvent.measure_index)
            .having(func.count(func.distinct(FeedbackEvent.domain)) == 3)
            .order_by(FeedbackEvent.session_id, FeedbackEvent.measure_index)
        )
        measures: dict[int, list[int]] = {}
        for session_id, measure_index in result.all():
            measures.setdefault(session_id, []).append(measure_index)
        return measures

    async def duet_video_ids(self, session_ids: list[int]) -> dict[int, int]:
        result = await self.session.execute(
            select(DuetVideo.session_id, DuetVideo.id).where(
                DuetVideo.session_id.in_(session_ids)
            )
        )
        return {session_id: duet_id for session_id, duet_id in result.all()}
