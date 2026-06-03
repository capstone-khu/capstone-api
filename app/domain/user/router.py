from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.user.model import User
from app.domain.user.schema import ProfileResponse

router = APIRouter(tags=["user"])


@router.get(
    "/me",
    summary="내 프로필 조회",
    response_model=ApiResponse[ProfileResponse, None],
    response_model_exclude_none=True,
    responses=error_responses(ErrorCode.UNAUTHORIZED),
)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[ProfileResponse, None]:
    data = ProfileResponse(
        id=current_user.id,
        name=current_user.name,
        created_at=current_user.created_at,
    )
    return ApiResponse.ok(SuccessCode.OK, data)
