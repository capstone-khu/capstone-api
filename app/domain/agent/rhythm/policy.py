from app.domain.agent.schema import ActionSpec, Domain

GOOD = "GOOD"
EARLY = "EARLY"
LATE = "LATE"
FAST = "FAST"
SLOW = "SLOW"

SCORE_GOOD = 0.80
DRIFT_TOLERANCE_MS = 80.0
BEAT_RATIO_FAST = 1.3

_SEVERITY = {GOOD: 0, FAST: 1, SLOW: 1, EARLY: 2, LATE: 2}

POSITIVE = ActionSpec(
    action_id="RH-01",
    action="POSITIVE_RHYTHM",
    feedback="잘 하고 있습니다. 계속 유지하세요",
)
RHYTHM_WAIT = ActionSpec(
    action_id="RH-02",
    action="RHYTHM_WAIT",
    feedback="박자보다 일찍 연주하고 있습니다. 박자를 맞추세요",
)
RHYTHM_CATCH_UP = ActionSpec(
    action_id="RH-03",
    action="RHYTHM_CATCH_UP",
    feedback="박자보다 늦게 연주하고 있습니다. 박자를 맞추세요",
)
TEMPO_SLOW_DOWN = ActionSpec(
    action_id="RH-04",
    action="TEMPO_SLOW_DOWN",
    feedback="템포가 빠릅니다. 속도를 늦추세요",
)
TEMPO_SPEED_UP = ActionSpec(
    action_id="RH-05",
    action="TEMPO_SPEED_UP",
    feedback="템포가 느립니다. 속도를 높이세요",
)
CALL_SUPERVISOR = ActionSpec(
    action_id="RH-00", action="CALL_SUPERVISOR", feedback="원인 분석 중"
)


def classify_rhythm(score: float, drift_ms: float, beat_ratio: float) -> str:
    if score >= SCORE_GOOD and abs(drift_ms) <= DRIFT_TOLERANCE_MS:
        return GOOD
    if drift_ms < -DRIFT_TOLERANCE_MS:
        return EARLY
    if drift_ms > DRIFT_TOLERANCE_MS:
        return LATE
    if beat_ratio > BEAT_RATIO_FAST:
        return FAST
    return SLOW


class RhythmPolicy:
    domain = Domain.RHYTHM

    def available_actions(self, state: str) -> list[ActionSpec]:
        if state == GOOD:
            return [POSITIVE]
        if state == EARLY:
            return [RHYTHM_WAIT, CALL_SUPERVISOR]
        if state == LATE:
            return [RHYTHM_CATCH_UP, CALL_SUPERVISOR]
        if state == FAST:
            return [TEMPO_SLOW_DOWN, CALL_SUPERVISOR]
        if state == SLOW:
            return [TEMPO_SPEED_UP, CALL_SUPERVISOR]
        return []

    def is_good(self, state: str) -> bool:
        return state == GOOD

    def severity(self, state: str) -> int:
        return _SEVERITY.get(state, 0)

    def same_group(self, prev: str, curr: str) -> bool:
        return True
