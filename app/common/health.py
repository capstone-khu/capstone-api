from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.common.persistence import engine

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness 체크",
    description="프로세스가 살아 있는지 확인한다. DB 등 의존성은 검사하지 않는다.",
    response_description="프로세스 상태",
    responses={
        200: {"content": {"application/json": {"example": {"status": "ok"}}}},
    },
)
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness 체크",
    description="트래픽을 받을 준비가 됐는지 확인한다. DB 연결(`SELECT 1`)까지 검사하며, 실패 시 `503` 을 반환한다.",
    response_description="준비 상태와 DB 연결 상태",
    responses={
        200: {"content": {"application/json": {"example": {"status": "ready", "db": "up"}}}},
        503: {
            "description": "DB 연결 실패 등으로 트래픽을 받을 수 없는 상태",
            "content": {"application/json": {"example": {"status": "not ready", "db": "down"}}},
        },
    },
)
async def readiness() -> JSONResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "db": "down"},
        )
    return JSONResponse(content={"status": "ready", "db": "up"})
