from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.session.schema import SessionCreateRequest, SessionCreateResponse
from app.domain.session.service import SessionService
from app.domain.user.model import User

router = APIRouter(prefix="/sessions", tags=["session"])


@router.post(
    "",
    status_code=201,
    summary="연주 세션 생성",
    description=(
        "연주 세션을 생성한다. `mode` 가 `duet` 이면 "
        "`partner_recording_id` 가 필요하다. "
        "협주 녹음은 존재해야 하고, 요청 곡의 녹음이며 "
        "본인 녹음이 아니어야 한다. "
        "응답은 곡명을 포함하며, `duet` 이면 협주 상대 이름과 "
        "라이브 재생용 음원 URL을 함께 반환한다."
    ),
    response_model=ApiResponse[SessionCreateResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            201,
            {
                "success": True,
                "status": 201,
                "message": "리소스가 생성되었습니다.",
                "data": {
                    "session_id": 12,
                    "status": "created",
                    "song_title": "반짝 반짝 작은별",
                    "partner_name": "손수민",
                    "audio_url": "/media/recordings/1.mp4",
                },
            },
        ),
        **error_responses(
            ErrorCode.INVALID_MAPPING_PARAMETER,
            ErrorCode.INVALID_DUET_PARTNER,
            ErrorCode.UNAUTHORIZED,
            ErrorCode.SONG_NOT_FOUND,
            ErrorCode.RECORDING_NOT_FOUND,
        ),
    },
)
async def create_session(
    request: SessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionCreateResponse, None]:
    data = await SessionService(db).create_session(current_user.id, request)
    return ApiResponse.created(SuccessCode.CREATED, data)
