from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.song.schema import SongListResponse
from app.domain.song.service import SongService
from app.domain.user.model import User

router = APIRouter(prefix="/songs", tags=["song"])


@router.get(
    "",
    summary="곡 목록 조회",
    description="연주 가능한 곡 목록을 조회한다.",
    response_model=ApiResponse[SongListResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "total": 1,
                    "songs": [{"id": 1, "number": 1, "title": "반짝 반짝 작은별"}],
                },
            },
        ),
        **error_responses(ErrorCode.UNAUTHORIZED),
    },
)
async def list_songs(
    _: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SongListResponse, None]:
    data = await SongService(db).list_songs()
    return ApiResponse.ok(SuccessCode.OK, data)
