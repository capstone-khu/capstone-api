from typing import Protocol

from app.domain.agent.schema import ActionSpec, Domain

REWARD_GOOD = 1.0
REWARD_PARTIAL = 0.5
REWARD_NO_CHANGE = -0.3
REWARD_WORSE = -0.8
REWARD_SUPERVISOR_HIT = 0.8
REWARD_SUPERVISOR_MISS = -0.5

DELEGATION_SUFFIX = "-00"


class Policy(Protocol):
    domain: Domain

    def available_actions(self, state: str) -> list[ActionSpec]: ...

    def is_good(self, state: str) -> bool: ...

    def severity(self, state: str) -> int: ...

    def same_group(self, prev: str, curr: str) -> bool: ...
