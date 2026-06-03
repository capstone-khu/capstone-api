from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.model import User


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_name(self, name: str) -> User | None:
        result = await self.session.execute(select(User).where(User.name == name))
        return result.scalar_one_or_none()
