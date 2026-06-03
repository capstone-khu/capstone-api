from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.common.persistence import get_db
from app.domain.auth.security import decode_token
from app.domain.user.model import User
from app.domain.user.repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise BusinessException(ErrorCode.UNAUTHORIZED)

    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise BusinessException(ErrorCode.UNAUTHORIZED) from None

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise BusinessException(ErrorCode.UNAUTHORIZED)
    return user
