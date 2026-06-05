from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.session.model import Recording, Session
from app.domain.user.model import User


class SessionRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        song_id: int,
        mode: str,
        partner_recording_id: int | None,
    ) -> Session:
        entity = Session(
            user_id=user_id,
            song_id=song_id,
            mode=mode,
            partner_recording_id=partner_recording_id,
            status="created",
        )
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_recording_with_partner(
        self, recording_id: int
    ) -> tuple[Recording, str] | None:
        result = await self.session.execute(
            select(Recording, User.name)
            .join(User, User.id == Recording.user_id)
            .where(Recording.id == recording_id)
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]
