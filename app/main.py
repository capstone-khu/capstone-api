from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common import health
from app.common.config import settings
from app.common.exception.handlers import add_exception_handlers

DESCRIPTION = """\
캡스톤 백엔드 API.

- 응답은 모두 `ApiResponse` 형식으로 내려가며, 값이 없는(`null`) 필드는 빼고 보낸다.
- 인증이 필요한 API는 `Authorization: Bearer <JWT>` 헤더가 있어야 한다.
- 요청이 실패하면 에러 코드(`code`)와 경로·시각(`meta`)이 함께 담긴다.
"""

TAGS_METADATA = [
    {"name": "health", "description": "서버 상태 확인."},
    {"name": "auth", "description": "로그인·로그아웃·JWT 발급."},
    {"name": "user", "description": "사용자 프로필·연주 이력·마이페이지."},
    {"name": "song", "description": "곡·악보·협주 상대 조회."},
    {"name": "session", "description": "연주 세션 생성·실시간 스트림·종료·결과·AI 분석."},
    {"name": "agent", "description": "멀티에이전트 코칭 피드백."},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=DESCRIPTION,
    version="0.1.0",
    debug=settings.DEBUG,
    openapi_tags=TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_exception_handlers(app)

app.include_router(health.router)
