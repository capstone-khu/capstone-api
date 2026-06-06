from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.repository import UserRepository
from app.domain.user.schema import HistoryItem, HistoryResponse, HistoryStats


class UserService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def get_history(self, user_id: int, page: int, size: int) -> HistoryResponse:
        total = await self.users.count_completed_sessions(user_id)
        rows = await self.users.completed_sessions_page(
            user_id, offset=(page - 1) * size, limit=size
        )

        session_ids = [session.id for session, _, _ in rows]
        counts: dict[int, dict[str, int]] = {}
        focus_measures: dict[int, list[int]] = {}
        duet_ids: dict[int, int] = {}
        if session_ids:
            counts = await self.users.problem_counts(session_ids)
            focus_measures = await self.users.focus_measures_by_session(session_ids)
            duet_ids = await self.users.duet_video_ids(session_ids)

        items = [
            HistoryItem(
                session_id=session.id,
                song_title=song_title,
                played_at=session.ended_at,
                mode=session.mode,
                stats=HistoryStats(
                    pitch=counts.get(session.id, {}).get("pitch", 0),
                    rhythm=counts.get(session.id, {}).get("rhythm", 0),
                    posture=counts.get(session.id, {}).get("posture", 0),
                ),
                focus_measures=focus_measures.get(session.id, []),
                duet_composite_id=duet_ids.get(session.id),
                partner_name=partner_name,
            )
            for session, song_title, partner_name in rows
        ]
        return HistoryResponse(page=page, size=size, total=total, items=items)
