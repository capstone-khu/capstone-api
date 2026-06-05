from app.domain.agent.schema import ActionSpec, Domain

GOOD = "GOOD"
LEFT_HAND_ALIGNMENT = "LEFT_HAND_ALIGNMENT"
SHOULDER_IMBALANCE = "SHOULDER_IMBALANCE"
LEFT_WRIST_MOVEMENT = "LEFT_WRIST_MOVEMENT"
LEFT_ARM_POSTURE = "LEFT_ARM_POSTURE"
RIGHT_ARM_BOWING = "RIGHT_ARM_BOWING"
RIGHT_WRIST_ALIGNMENT = "RIGHT_WRIST_ALIGNMENT"
OTHER = "OTHER"

FEATURE_STATE = {
    0: LEFT_HAND_ALIGNMENT,
    1: SHOULDER_IMBALANCE,
    2: LEFT_WRIST_MOVEMENT,
    3: LEFT_ARM_POSTURE,
    4: RIGHT_ARM_BOWING,
    5: RIGHT_WRIST_ALIGNMENT,
}

POSITIVE = ActionSpec(
    action_id="PS-01",
    action="POSITIVE_POSTURE",
    feedback="잘 하고 있습니다. 계속 유지하세요",
)
HAND_ALIGNMENT_CORRECT = ActionSpec(
    action_id="PS-02",
    action="HAND_ALIGNMENT_CORRECT",
    feedback="왼손과 어깨 사이 거리를 안정적으로 유지하세요.",
)
SHOULDER_BALANCE = ActionSpec(
    action_id="PS-03",
    action="SHOULDER_BALANCE",
    feedback="양쪽 어깨 높이를 균형 있게 맞추세요.",
)
WRIST_STRAIGHTEN = ActionSpec(
    action_id="PS-04",
    action="WRIST_STRAIGHTEN",
    feedback="왼손목 움직임을 줄이고 중심을 안정적으로 잡으세요.",
)
ARM_POSTURE_CORRECT = ActionSpec(
    action_id="PS-05",
    action="ARM_POSTURE_CORRECT",
    feedback="왼팔 각도를 안정적으로 유지하세요.",
)
ARM_STRAIGHTEN = ActionSpec(
    action_id="PS-06",
    action="ARM_STRAIGHTEN",
    feedback="오른팔 보잉 각도를 자연스럽게 펴세요.",
)
WRIST_ALIGNMENT = ActionSpec(
    action_id="PS-07",
    action="WRIST_ALIGNMENT",
    feedback="오른손목을 세우고 보잉 방향을 안정적으로 유지하세요.",
)
CORRECT_POSTURE = ActionSpec(
    action_id="PS-99",
    action="CORRECT_POSTURE",
    feedback="자세를 안정적으로 교정하세요.",
)
CALL_SUPERVISOR = ActionSpec(
    action_id="PS-00", action="CALL_SUPERVISOR", feedback="원인 분석 중"
)

_CORRECTION = {
    LEFT_HAND_ALIGNMENT: HAND_ALIGNMENT_CORRECT,
    SHOULDER_IMBALANCE: SHOULDER_BALANCE,
    LEFT_WRIST_MOVEMENT: WRIST_STRAIGHTEN,
    LEFT_ARM_POSTURE: ARM_POSTURE_CORRECT,
    RIGHT_ARM_BOWING: ARM_STRAIGHTEN,
    RIGHT_WRIST_ALIGNMENT: WRIST_ALIGNMENT,
}


def classify_posture(stable: bool, top_feature_index: int | None) -> str:
    if stable or top_feature_index is None:
        return GOOD
    return FEATURE_STATE.get(top_feature_index, OTHER)


class PosturePolicy:
    domain = Domain.POSTURE

    def available_actions(self, state: str) -> list[ActionSpec]:
        if state == GOOD:
            return [POSITIVE]
        correction = _CORRECTION.get(state, CORRECT_POSTURE)
        return [correction, CALL_SUPERVISOR]

    def is_good(self, state: str) -> bool:
        return state == GOOD

    def severity(self, state: str) -> int:
        return 0 if state == GOOD else 1

    def same_group(self, prev: str, curr: str) -> bool:
        return False
