from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.song.schema import (
    DuetPartnersResponse,
    ScoreResponse,
    SongListResponse,
)
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


@router.get(
    "/{song_id}/score",
    summary="악보 조회",
    description="한 곡의 악보를 마디·음표·가사 단위로 조회한다.",
    response_model=ApiResponse[ScoreResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "song": {
                        "id": 1,
                        "number": 1,
                        "title": "반짝 반짝 작은별",
                        "bpm": 96,
                        "time_signature": "4/4",
                        "total_measures": 12,
                    },
                    "measures": [
                        {
                            "measure_index": 1,
                            "notes": [
                                {
                                    "pitch": "D4",
                                    "duration": "quarter",
                                    "position": 0,
                                    "lyric": "반",
                                }
                            ],
                        }
                    ],
                },
            },
        ),
        **error_responses(ErrorCode.UNAUTHORIZED, ErrorCode.SONG_NOT_FOUND),
    },
)
async def get_score(
    song_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ScoreResponse, None]:
    data = await SongService(db).get_score(song_id)
    return ApiResponse.ok(SuccessCode.OK, data)


@router.get(
    "/{song_id}/duet-partners",
    summary="협주 상대 목록 조회",
    description=(
        "해당 곡으로 녹음이 있는 다른 연주자(협주 상대) 목록을 조회한다. "
        "요청자 본인의 녹음은 제외한다."
    ),
    response_model=ApiResponse[DuetPartnersResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "song_title": "반짝 반짝 작은별",
                    "partners": [
                        {
                            "recording_id": 1,
                            "user_name": "손수민",
                            "recorded_at": "2026-06-01T10:00:00+09:00",
                        }
                    ],
                },
            },
        ),
        **error_responses(ErrorCode.UNAUTHORIZED, ErrorCode.SONG_NOT_FOUND),
    },
)
async def list_duet_partners(
    song_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DuetPartnersResponse, None]:
    data = await SongService(db).list_duet_partners(song_id, current_user.id)
    return ApiResponse.ok(SuccessCode.OK, data)
