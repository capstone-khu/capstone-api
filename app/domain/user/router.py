from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.user.model import User
from app.domain.user.schema import HistoryResponse, ProfileResponse
from app.domain.user.service import UserService

router = APIRouter(tags=["user"])


@router.get(
    "/me",
    summary="내 프로필 조회",
    description=(
        "현재 로그인한 사용자의 프로필을 조회한다. "
        "`Authorization: Bearer <JWT>` 헤더가 필요하다."
    ),
    response_model=ApiResponse[ProfileResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "id": 1,
                    "name": "신진수",
                    "created_at": "2026-06-01T10:00:00+09:00",
                },
            },
        ),
        **error_responses(ErrorCode.UNAUTHORIZED),
    },
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


@router.get(
    "/me/history",
    summary="연주 이력 조회",
    description=(
        "내 연주 이력을 페이지 단위(기본 3개)로 조회한다. "
        "완료(`completed`) 세션만 `played_at` 내림차순으로 반환하며, "
        "각 항목은 영역별 문제 개수(`state != GOOD`) 통계와 "
        "집중 반복 필요 마디(`focus_measures`)를 포함한다. "
        "협주 기록이면 합성 영상 ID(`duet_composite_id`)와 "
        "협주 상대 이름(`partner_name`)을 함께 반환한다."
    ),
    response_model=ApiResponse[HistoryResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "page": 1,
                    "size": 3,
                    "total": 7,
                    "items": [
                        {
                            "session_id": 12,
                            "song_title": "반짝 반짝 작은별",
                            "played_at": "2026-06-02T09:30:00+09:00",
                            "mode": "duet",
                            "stats": {"pitch": 3, "rhythm": 1, "posture": 2},
                            "focus_measures": [5, 7],
                            "duet_composite_id": 5,
                            "partner_name": "이준호",
                        },
                        {
                            "session_id": 10,
                            "song_title": "반짝 반짝 작은별",
                            "played_at": "2026-06-01T18:10:00+09:00",
                            "mode": "solo",
                            "stats": {"pitch": 0, "rhythm": 2, "posture": 1},
                            "focus_measures": [],
                        },
                    ],
                },
            },
        ),
        **error_responses(ErrorCode.UNAUTHORIZED),
    },
)
async def get_my_history(
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1)] = 3,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[HistoryResponse, None]:
    data = await UserService(db).get_history(current_user.id, page, size)
    return ApiResponse.ok(SuccessCode.OK, data)
