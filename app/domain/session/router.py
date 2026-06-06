from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode
from app.common.openapi import error_responses, success_response
from app.common.persistence import get_db
from app.common.response import ApiResponse
from app.domain.auth.dependencies import get_current_user
from app.domain.session.schema import (
    MeasureDetailResponse,
    PreviousMarkingsResponse,
    SessionAnalysisResponse,
    SessionCompleteResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResultResponse,
)
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
    "/{session_id}/complete",
    summary="연주 세션 종료",
    description=(
        "연주를 정상 종료한다. 녹음(audio)·녹화(video)를 multipart 로 업로드해 "
        "media 볼륨에 저장하고 녹음행을 만든 뒤, 실시간 동안 모은 피드백·Q 를 "
        "일괄 영속하고 세션을 `completed` 로 닫는다. 협주(duet) 세션이면 합성 영상 "
        "잡을 트리거하고 `duet_composite_id` 를 함께 반환한다. "
        "본인 세션 아니면 403, 없으면 404, 이미 종료면 409."
    ),
    response_model=ApiResponse[SessionCompleteResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "session_id": 12,
                    "recording_id": 21,
                    "duet_composite_id": 5,
                },
            },
        ),
        **error_responses(
            ErrorCode.INVALID_MAPPING_PARAMETER,
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.SESSION_ALREADY_ENDED,
        ),
    },
)
async def complete_session(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    background: BackgroundTasks,
    audio: Annotated[UploadFile, File()],
    video: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionCompleteResponse, None]:
    data = await SessionService(db).complete_session(
        current_user.id, session_id, audio, video, background
    )
    return ApiResponse.ok(SuccessCode.OK, data)


@router.get(
    "/{session_id}/previous-markings",
    summary="직전 세션 마킹 조회",
    description=(
        "연주 화면 진입 시 직전 완료 세션의 마디별 마킹(외곽선)을 미리 조회한다. "
        "같은 사용자·곡의 모드에 무관하게 직전 `completed` 세션 기준이다."
        "(`state != GOOD`)만 반환한다. 직전 완료 세션이 없으면 빈 배열로 내려준다."
    ),
    response_model=ApiResponse[PreviousMarkingsResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "previous_session_id": 10,
                    "measures": [
                        {
                            "measure_index": 4,
                            "markings": [
                                {
                                    "domain": "pitch",
                                    "action_id": "PT-03",
                                    "feedback": "음정을 내리세요",
                                }
                            ],
                        }
                    ],
                },
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
        ),
    },
)
async def previous_markings(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PreviousMarkingsResponse, None]:
    data = await SessionService(db).previous_markings(current_user.id, session_id)
    return ApiResponse.ok(SuccessCode.OK, data)


@router.get(
    "/{session_id}/result",
    summary="세션 결과 마킹 조회",
    description=(
        "세션의 마디별 누적 마킹을 조회한다. "
        "이번 세션은 채움 표시(current), 직전 완료 세션은 "
        "외곽선 표시(previous)로 반환한다. "
        "마킹은 문제 마디(`state != GOOD`)만 포함한다. "
        "직전 완료 세션이 없으면 previous 는 빈 배열이다. "
        "완료되지 않은 세션이면 409 를 반환한다."
    ),
    response_model=ApiResponse[SessionResultResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "session_id": 12,
                    "song_id": 1,
                    "song_title": "반짝 반짝 작은별",
                    "played_at": "2026-06-02T09:30:00+09:00",
                    "mode": "duet",
                    "partner_name": "손수민",
                    "measures": [
                        {
                            "measure_index": 1,
                            "current": [
                                {
                                    "domain": "pitch",
                                    "action_id": "PT-03",
                                    "feedback": "음정을 내리세요",
                                }
                            ],
                            "previous": [
                                {
                                    "domain": "rhythm",
                                    "action_id": "RH-03",
                                    "feedback": "박자보다 늦게 연주하고 있습니다",
                                }
                            ],
                        }
                    ],
                },
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.SESSION_NOT_COMPLETED,
        ),
    },
)
async def get_session_result(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionResultResponse, None]:
    data = await SessionService(db).get_session_result(current_user.id, session_id)
    return ApiResponse.ok(SuccessCode.OK, data)


@router.get(
    "/{session_id}/measures/{measure_index}",
    summary="마디 상세 조회",
    description=(
        "결과 화면의 마디 상세 모달 데이터를 조회한다. "
        "해당 마디의 음표 배열과 이번 세션·직전 세션의 "
        "마킹(`state != GOOD`)을 함께 반환한다. "
        "직전 완료 세션이 없으면 previous_markings 는 빈 배열이다. "
        "곡에 없는 마디면 404 를 반환한다."
    ),
    response_model=ApiResponse[MeasureDetailResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "measure_index": 1,
                    "notes": [
                        {
                            "pitch": "D4",
                            "duration": "quarter",
                            "position": 0,
                            "lyric": "반",
                        }
                    ],
                    "current_markings": [
                        {
                            "domain": "pitch",
                            "action_id": "PT-03",
                            "feedback": "음정을 내리세요",
                        }
                    ],
                    "previous_markings": [],
                },
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.MEASURE_NOT_FOUND,
        ),
    },
)
async def get_measure_detail(
    session_id: int,
    measure_index: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MeasureDetailResponse, None]:
    data = await SessionService(db).get_measure_detail(
        current_user.id, session_id, measure_index
    )
    return ApiResponse.ok(SuccessCode.OK, data)


@router.get(
    "/{session_id}/analysis",
    summary="AI 상세 분석 조회",
    description=(
        "세션의 AI 상세 분석을 조회한다. "
        "저장된 리포트가 없으면 첫 호출에서 LLM 으로 동기 생성(수 초 블로킹)한 뒤 "
        "캐시하고, 이후 같은 세션은 저장본을 반환한다. "
        "`focus_measures` 는 캐시와 무관하게 매번 도출한다. "
        "완료되지 않은 세션이면 409, LLM 생성 실패 시 저장 없이 503 을 반환한다."
    ),
    response_model=ApiResponse[SessionAnalysisResponse, None],
    response_model_exclude_none=True,
    responses={
        **success_response(
            200,
            {
                "success": True,
                "status": 200,
                "message": "요청에 성공했습니다.",
                "data": {
                    "session_id": 12,
                    "headline": "이번엔 음정이 제일 아쉬웠어요",
                    "coach_comment": (
                        "음정이 자주 흔들렸고, 자세가 무너질 때 "
                        "음정도 같이 흔들렸어요."
                    ),
                    "domains": {
                        "pitch": {
                            "level": "weak",
                            "diagnosis": "높은 음에서 음정이 올라갔어요",
                            "practice": "스케일을 천천히 반복해보세요",
                        },
                        "rhythm": {
                            "level": "ok",
                            "diagnosis": "일부 구간에서 살짝 늦었어요",
                            "practice": "메트로놈에 맞춰 연습해보세요",
                        },
                        "posture": {
                            "level": "good",
                            "diagnosis": "자세는 안정적이었어요",
                        },
                    },
                    "focus_measures": [5, 7],
                },
            },
        ),
        **error_responses(
            ErrorCode.UNAUTHORIZED,
            ErrorCode.FORBIDDEN_SESSION,
            ErrorCode.SESSION_NOT_FOUND,
            ErrorCode.SESSION_NOT_COMPLETED,
            ErrorCode.ANALYSIS_GENERATION_FAILED,
        ),
    },
)
async def get_session_analysis(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionAnalysisResponse, None]:
    data = await SessionService(db).get_session_analysis(current_user.id, session_id)
    return ApiResponse.ok(SuccessCode.OK, data)


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
