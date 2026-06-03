from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.schema import LoginRequest, LoginResponse
from app.domain.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    summary="로그인",
    response_model=ApiResponse[LoginResponse, None],
    response_model_exclude_none=True,
    responses=error_responses(ErrorCode.LOGIN_FAILED),
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LoginResponse, None]:
    data = await AuthService(db).login(request)
    return ApiResponse.ok(SuccessCode.OK, data)
