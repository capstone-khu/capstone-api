from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.domain.auth.schema import LoginRequest, LoginResponse, UserSummary
from app.domain.auth.security import create_access_token, verify_password
from app.domain.user.repository import UserRepository


class AuthService:

    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def login(self, request: LoginRequest) -> LoginResponse:
        user = await self.users.get_by_name(request.name)
        if user is None or not verify_password(request.password, user.password_hash):
            raise BusinessException(ErrorCode.LOGIN_FAILED)

        token = create_access_token(user.id)
        return LoginResponse(
            access_token=token,
            user=UserSummary(id=user.id, name=user.name),
        )
