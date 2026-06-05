import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.common import health
from app.common.config import settings
from app.common.exception.handlers import add_exception_handlers
from app.common.media import sync_seed_media
from app.domain.agent.realtime.warmup import warm_blocking
from app.domain.auth import router as auth_router
from app.domain.session import duet_router as session_duet_router
from app.domain.session import router as session_router
from app.domain.session import ws as session_ws
from app.domain.song import router as song_router
from app.domain.user import router as user_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_seed_media()
    asyncio.create_task(_warmup())
    yield


async def _warmup() -> None:
    """부팅 직후 실시간 측정 스택을 백그라운드로 워밍업 한다(서빙 차단 안 함)."""
    try:
        await asyncio.get_event_loop().run_in_executor(None, warm_blocking)
    except Exception:
        logger.exception("워밍업 태스크 실패")

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
    {
        "name": "session",
        "description": "연주 세션 생성·실시간 스트림·종료·결과·AI 분석.",
    },
    {"name": "agent", "description": "멀티에이전트 코칭 피드백."},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=DESCRIPTION,
    version="0.1.0",
    debug=settings.DEBUG,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

app.mount(
    "/media",
    StaticFiles(directory=settings.MEDIA_ROOT, check_dir=False),
    name="media",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(song_router.router)
app.include_router(session_router.router)
app.include_router(session_ws.router)
app.include_router(session_duet_router.router)
app.include_router(user_router.router)
