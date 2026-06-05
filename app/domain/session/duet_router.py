from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.session.schema import DuetVideoResponse
from app.domain.session.service import SessionService
from app.domain.user.model import User

router = APIRouter(prefix="/duet-videos", tags=["user"])


@router.get(
    "/{duet_composite_id}",
    summary="협주 합성 영상 단건 조회",
    description=(
        "협주 합성 영상 1건의 상태를 조회한다. "
        "`POST /sessions/{id}/complete` 가 돌려준 `duet_composite_id` 로 "
        "합성 진행 상태를 폴링한다(pending → processing → ready/failed)."
    ),
    response_model=ApiResponse[DuetVideoResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "duet_composite_id": 5,
                    "song_title": "반짝 반짝 작은별",
                    "partner_name": "손수민",
                    "status": "ready",
                    "composite_video_url": "/media/duet/5.mp4",
                    "created_at": "2026-06-02T09:35:00+09:00",
                },
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_DUET,
            ErrorCode.DUET_NOT_FOUND,
        ),
    },
)
async def get_duet_video(
    duet_composite_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DuetVideoResponse, None]:
    data = await SessionService(db).get_duet_video(current_user.id, duet_composite_id)
    return ApiResponse.ok(SuccessCode.OK, data)
