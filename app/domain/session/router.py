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


@router.post(
    "/{session_id}/abort",
    summary="연주 세션 중도 종료",
    description=(
        "연주를 중도 종료한다. 이번 연주는 저장하지 않고 세션을 `aborted` 로 닫는다. "
        "본인 세션이 아니면 403, 없는 세션이면 404, "
        "이미 종료된 세션이면 409로 막는다."
    ),
    response_model=ApiResponse[None, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.SESSION_ALREADY_ENDED,
        ),
    },
)
async def abort_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None, None]:
    await SessionService(db).abort_session(current_user.id, session_id)
    return ApiResponse.ok(SuccessCode.OK)
