from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Domain(StrEnum):
    PITCH = "pitch"
    RHYTHM = "rhythm"
    POSTURE = "posture"


class AgentOutput(BaseModel):
    domain: Domain
    measure_index: int
    state: str
    action_id: str
    action: str
    feedback: str
    reward: float | None = None
    q: float
    cause_domain: str | None = None
    meta: dict[str, Any] | None = None
