from app.domain.agent.schema import ActionSpec, Domain

SLIGHT_THRESHOLD = 30.0
MAJOR_THRESHOLD = 100.0

GOOD = "GOOD"
SHARP_SLIGHT = "SHARP_SLIGHT"
SHARP_MAJOR = "SHARP_MAJOR"
FLAT_SLIGHT = "FLAT_SLIGHT"
FLAT_MAJOR = "FLAT_MAJOR"

_SEVERITY = {GOOD: 0, SHARP_SLIGHT: 1, FLAT_SLIGHT: 1, SHARP_MAJOR: 2, FLAT_MAJOR: 2}
_SHARP_GROUP = {SHARP_SLIGHT, SHARP_MAJOR}
_FLAT_GROUP = {FLAT_SLIGHT, FLAT_MAJOR}

POSITIVE = ActionSpec(
    action_id="PT-01",
    action="POSITIVE_PITCH",
    feedback="잘 하고 있습니다. 계속 유지하세요",
)
PITCH_UP = ActionSpec(
    action_id="PT-02", action="PITCH_UP", feedback="음정을 올리세요"
)
PITCH_DOWN = ActionSpec(
    action_id="PT-03", action="PITCH_DOWN", feedback="음정을 내리세요"
)
CALL_SUPERVISOR = ActionSpec(
    action_id="PT-00", action="CALL_SUPERVISOR", feedback="원인 분석 중"
)


def classify_cents(avg_cents: float) -> str:
    abs_dev = abs(avg_cents)
    if abs_dev < SLIGHT_THRESHOLD:
        return GOOD
    if avg_cents > 0:
        return SHARP_MAJOR if avg_cents >= MAJOR_THRESHOLD else SHARP_SLIGHT
    return FLAT_MAJOR if abs_dev >= MAJOR_THRESHOLD else FLAT_SLIGHT


class PitchPolicy:
    domain = Domain.PITCH

    def available_actions(self, state: str) -> list[ActionSpec]:
        if state == GOOD:
            return [POSITIVE]
        if state in _SHARP_GROUP:
            return [PITCH_DOWN, CALL_SUPERVISOR]
        if state in _FLAT_GROUP:
            return [PITCH_UP, CALL_SUPERVISOR]
        return []

    def is_good(self, state: str) -> bool:
        return state == GOOD

    def severity(self, state: str) -> int:
        return _SEVERITY.get(state, 0)

    def same_group(self, prev: str, curr: str) -> bool:
        return (prev in _SHARP_GROUP and curr in _SHARP_GROUP) or (
            prev in _FLAT_GROUP and curr in _FLAT_GROUP
        )
