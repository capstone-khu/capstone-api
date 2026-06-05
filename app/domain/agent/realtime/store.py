from app.domain.agent.realtime.runtime import LiveSession

LIVE_SESSIONS: dict[int, LiveSession] = {}


def register(live: LiveSession) -> None:
    LIVE_SESSIONS[live.session_id] = live


def get(session_id: int) -> LiveSession | None:
    return LIVE_SESSIONS.get(session_id)


def pop(session_id: int) -> LiveSession | None:
    return LIVE_SESSIONS.pop(session_id, None)
