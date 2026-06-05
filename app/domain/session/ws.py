import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func

from app.common.persistence import AsyncSessionLocal
from app.domain.agent.realtime import store
from app.domain.agent.realtime.runtime import LiveSession
from app.domain.agent.realtime.supervisor import resolve_cause
from app.domain.agent.schema import AgentOutput, Domain
from app.domain.auth.security import decode_token
from app.domain.session.model import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["session"])

CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_ALREADY_ENDED = 4409
CLOSE_INTERNAL = 1011

_DELEGATION = "-00"
_TIE = {Domain.POSTURE: 0, Domain.PITCH: 1, Domain.RHYTHM: 2}


@router.websocket("/sessions/{session_id}/stream")
async def stream(websocket: WebSocket, session_id: int) -> None:
    await websocket.accept()

    user_id = _authenticate(websocket)
    if user_id is None:
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            await websocket.close(code=CLOSE_NOT_FOUND)
            return
        if session.user_id != user_id:
            await websocket.close(code=CLOSE_FORBIDDEN)
            return
        if session.status in ("completed", "aborted"):
            await websocket.close(code=CLOSE_ALREADY_ENDED)
            return

        from app.domain.agent.realtime.aggregator import build_live_session

        live = await build_live_session(db, session)
        session.status = "in_progress"
        session.started_at = func.now()
        await db.commit()

    store.register(live)
    executor = ThreadPoolExecutor(max_workers=1)
    send_lock = asyncio.Lock()
    tasks: set[asyncio.Task] = set()
    try:
        await _loop(websocket, live, executor, send_lock, tasks)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS stream 처리 중 오류 (session_id=%s)", session_id)
        await websocket.close(code=CLOSE_INTERNAL)
    finally:
        for task in tasks:
            task.cancel()
        executor.shutdown(wait=False)
        await _cleanup(session_id)


def _authenticate(websocket: WebSocket) -> int | None:
    token = websocket.query_params.get("token")
    if token is None:
        header = websocket.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:]
    if not token:
        return None
    try:
        return int(decode_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


async def _loop(
    websocket: WebSocket,
    live: LiveSession,
    executor: ThreadPoolExecutor,
    send_lock: asyncio.Lock,
    tasks: set[asyncio.Task],
) -> None:
    loop = asyncio.get_event_loop()
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return

        payload = message.get("bytes")
        if payload is not None:
            kind = payload[0]
            ts_ms = int.from_bytes(payload[1:5], "big")
            await loop.run_in_executor(executor, live.feed, kind, ts_ms, payload[5:])
            continue

        text = message.get("text")
        if text is None:
            continue
        data = json.loads(text)
        if data.get("type") == "measure":
            measure_index = int(data["measure_index"])
            outputs = await loop.run_in_executor(
                executor, live.score_measure, measure_index
            )
            async with send_lock:
                await websocket.send_json(
                    {
                        "type": "feedback",
                        "measure_index": measure_index,
                        "items": _items(outputs),
                    }
                )
            _spawn_resolvers(websocket, live, outputs, send_lock, tasks)


def _spawn_resolvers(
    websocket: WebSocket,
    live: LiveSession,
    outputs: list[AgentOutput],
    send_lock: asyncio.Lock,
    tasks: set[asyncio.Task],
) -> None:
    delegated = [o for o in outputs if o.action_id.endswith(_DELEGATION)]
    if not delegated:
        return
    states = {o.domain: o.state for o in outputs}
    metas = {o.domain: (o.meta or {}) for o in outputs}
    for output in delegated:
        task = asyncio.create_task(
            _resolve(websocket, live, output, states, metas, send_lock)
        )
        tasks.add(task)
        task.add_done_callback(tasks.discard)


async def _resolve(
    websocket: WebSocket,
    live: LiveSession,
    output: AgentOutput,
    states: dict[Domain, str],
    metas: dict[Domain, dict],
    send_lock: asyncio.Lock,
) -> None:
    cause, feedback = await resolve_cause(output.domain, states, metas)
    live.resolve_output(output.measure_index, output.domain, cause, feedback)
    item = {
        "domain": output.domain.value,
        "action_id": output.action_id,
        "action": output.action,
        "feedback": feedback,
        "cause": {"pending": False, "domain": cause},
    }
    try:
        async with send_lock:
            await websocket.send_json(
                {
                    "type": "feedback_update",
                    "measure_index": output.measure_index,
                    "item": item,
                }
            )
    except Exception:
        pass


def _items(outputs: list[AgentOutput]) -> list[dict]:
    def order(output: AgentOutput) -> tuple:
        return (
            output.reward is None,
            output.reward if output.reward is not None else 0.0,
            _TIE[output.domain],
        )

    items: list[dict] = []
    for output in sorted(outputs, key=order):
        item = {
            "domain": output.domain.value,
            "action_id": output.action_id,
            "action": output.action,
            "feedback": output.feedback,
        }
        if output.action_id.endswith(_DELEGATION):
            item["cause"] = {"pending": True}
        items.append(item)
    return items


async def _cleanup(session_id: int) -> None:
    live = store.pop(session_id)
    if live is None:
        return
    live.close()
    if live.completed:
        return
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is not None and session.status == "in_progress":
            session.status = "aborted"
            session.ended_at = func.now()
            await db.commit()
