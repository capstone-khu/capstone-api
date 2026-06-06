from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent.model import FeedbackEvent, QTableEntry
from app.domain.agent.schema import AgentOutput


class AgentRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_q_table(self, user_id: int) -> list[QTableEntry]:
        result = await self.session.execute(
            select(QTableEntry).where(QTableEntry.user_id == user_id)
        )
        return list(result.scalars().all())

    async def markings_for_session(self, session_id: int) -> list[FeedbackEvent]:
        result = await self.session.execute(
            select(FeedbackEvent)
            .where(
                FeedbackEvent.session_id == session_id,
                FeedbackEvent.state != "GOOD",
            )
            .order_by(FeedbackEvent.measure_index)
        )
        return list(result.scalars().all())

    async def markings_for_measure(
        self, session_id: int, measure_index: int
    ) -> list[FeedbackEvent]:
        result = await self.session.execute(
            select(FeedbackEvent).where(
                FeedbackEvent.session_id == session_id,
                FeedbackEvent.measure_index == measure_index,
                FeedbackEvent.state != "GOOD",
            )
        )
        return list(result.scalars().all())

    async def upsert_q_values(
        self, user_id: int, entries: list[dict]
    ) -> None:
        if not entries:
            return
        rows = [
            {
                "user_id": user_id,
                "domain": entry["domain"],
                "state": entry["state"],
                "action": entry["action"],
                "q_value": entry["q_value"],
                "update_count": entry["update_count"],
            }
            for entry in entries
        ]
        stmt = mysql_insert(QTableEntry).values(rows)
        stmt = stmt.on_duplicate_key_update(
            q_value=stmt.inserted.q_value,
            update_count=stmt.inserted.update_count,
        )
        await self.session.execute(stmt)

    async def insert_feedback_events(
        self, session_id: int, outputs: list[AgentOutput]
    ) -> None:
        if not outputs:
            return
        self.session.add_all(
            [
                FeedbackEvent(
                    session_id=session_id,
                    measure_index=output.measure_index,
                    domain=output.domain.value,
                    state=output.state,
                    action_id=output.action_id,
                    action=output.action,
                    feedback=output.feedback,
                    reward=output.reward,
                    q=output.q,
                    cause_domain=output.cause_domain,
                    meta=output.meta,
                )
                for output in outputs
            ]
        )
