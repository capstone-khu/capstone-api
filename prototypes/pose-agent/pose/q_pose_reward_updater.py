from collections import defaultdict
from dataclasses import dataclass
import random

import numpy as np


@dataclass(frozen=True)
class PoseQState:
    name: str

    def as_tuple(self):
        return self.name


class Q_PoseRewardUpdater:
    CALL_SUPERVISOR = "CALL_SUPERVISOR"

    DEFAULT_STATE_ACTIONS = {
        "GOOD": ("POSITIVE_T", CALL_SUPERVISOR),
        "LEFT_HAND_ALIGNMENT": ("HAND_ALIGNMENT_CORRECT", CALL_SUPERVISOR),
        "SHOULDER_IMBALANCE": ("SHOULDER_BALANCE", CALL_SUPERVISOR),
        "LEFT_WRIST_MOVEMENT": ("WRIST_STRAIGHTEN", CALL_SUPERVISOR),
        "LEFT_ARM_POSTURE": ("ARM_POSTURE_CORRECT", CALL_SUPERVISOR),
        "RIGHT_ARM_BOWING": ("ARM_STRAIGHTEN", CALL_SUPERVISOR),
        "RIGHT_WRIST_ALIGNMENT": ("WRIST_ALIGNMENT", CALL_SUPERVISOR),
    }

    FEATURE_STATE_MAP = {
        0: "LEFT_HAND_ALIGNMENT",
        1: "SHOULDER_IMBALANCE",
        2: "LEFT_WRIST_MOVEMENT",
        3: "LEFT_ARM_POSTURE",
        4: "RIGHT_ARM_BOWING",
        5: "RIGHT_WRIST_ALIGNMENT",
    }

    STABLE_STATE = "GOOD"

    ACTION_IDS = {
        "POSITIVE_T": "PA-00",
        "HAND_ALIGNMENT_CORRECT": "PA-01",
        "SHOULDER_BALANCE": "PA-02",
        "WRIST_STRAIGHTEN": "PA-03",
        "ARM_POSTURE_CORRECT": "PA-04",
        "ARM_STRAIGHTEN": "PA-05",
        "WRIST_ALIGNMENT": "PA-06",
        CALL_SUPERVISOR: "SA-00",
        "CORRECT_POSTURE": "PA-99",
    }

    DEFAULT_FEEDBACK = {
        "POSITIVE_T": "좋은 자세입니다. 지금 자세를 유지하세요.",
        "HAND_ALIGNMENT_CORRECT": "왼손과 어깨 사이 거리를 안정적으로 유지하세요.",
        "SHOULDER_BALANCE": "양쪽 어깨 높이를 균형 있게 맞추세요.",
        "WRIST_STRAIGHTEN": "왼손목 움직임을 줄이고 중심을 안정적으로 잡으세요.",
        "ARM_POSTURE_CORRECT": "왼팔 각도를 안정적으로 유지하세요.",
        "ARM_STRAIGHTEN": "오른팔 보잉 각도를 자연스럽게 펴세요.",
        "WRIST_ALIGNMENT": "오른손목을 세우고 보잉 방향을 안정적으로 유지하세요.",
        CALL_SUPERVISOR: "상위 Supervisor에게 자세 판단을 위임합니다.",
        "CORRECT_POSTURE": "자세를 안정적으로 교정하세요.",
    }

    def __init__(
        self,
        state_actions=None,
        alpha=0.1,
        gamma=0.9,
        epsilon=0.1,
    ):
        self.state_actions = dict(state_actions or self.DEFAULT_STATE_ACTIONS)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        self.q_table = defaultdict(dict)
        self.prev_state = None
        self.prev_action = None
        self.problem_states = set()
        self.last_improved_states = []

        for state_name in self.state_actions:
            self._ensure_state(state_name)

    def step(self, state, feedback=None, reward=None, next_state=None):
        if (
            self.prev_state is not None
            and self.prev_action is not None
            and reward is not None
            and next_state is not None
        ):
            self.update(
                self.prev_state,
                self.prev_action,
                reward,
                next_state,
            )

        action = self.choose_action(state, feedback=feedback)
        self.prev_state = state
        self.prev_action = action
        return action

    def get_state(self, result, prev_state=None):
        state_name = self._state_name_from_result(result)
        current_problem_states = self._problem_state_names_from_result(result)

        if state_name == self.STABLE_STATE:
            self.last_improved_states = sorted(self.problem_states)
            self.problem_states.clear()
        else:
            self.problem_states.update(current_problem_states)
            self.last_improved_states = []

        self._ensure_state(state_name)
        return PoseQState(name=state_name)

    def choose_action(self, state, feedback=None):
        state_name = self._state_name(state)
        actions = self._actions_for_state(state_name)

        if state_name == self.STABLE_STATE:
            return actions[0]

        if random.random() < self.epsilon:
            return random.choice(actions)

        q_values = self.q_table[state_name]
        return max(
            actions,
            key=lambda action: (
                q_values[action],
                -actions.index(action),
            ),
        )

    def execute_action(self, action, feedback):
        return {
            "action_id": self.action_id(action),
            "action": action,
            "feedback": self.feedback_text(action, feedback),
        }

    def compute_reward(
        self,
        previous_result,
        current_result,
        previous_state=None,
        current_state=None,
    ):
        previous_score = float(previous_result.get("final_score", 0.0))
        current_score = float(current_result.get("final_score", 0.0))

        score_delta = previous_score - current_score
        reward = score_delta / 100.0
        reward += self._case_reward(
            previous_result.get("case"),
            current_result.get("case"),
        )

        if current_state is not None and current_state.name == self.STABLE_STATE:
            reward += 0.2

        reward = float(np.clip(reward, -1.0, 1.0))

        return {
            "reward": reward,
            "reason": self._reward_reason(score_delta, reward),
            "score_delta": round(score_delta, 4),
        }

    def update(self, state, action, reward, next_state):
        state_name = self._state_name(state)
        next_state_name = self._state_name(next_state)

        self._ensure_state(state_name)
        self._ensure_state(next_state_name)

        updated_q = self._update_one(state_name, action, reward, next_state_name)

        if next_state_name == self.STABLE_STATE:
            for improved_state in self.last_improved_states:
                if improved_state != state_name:
                    improved_action = self._actions_for_state(improved_state)[0]
                    self._update_one(
                        improved_state,
                        improved_action,
                        reward,
                        next_state_name,
                    )

        return updated_q

    def evaluate_transition(
        self,
        previous_result,
        current_result,
        previous_state,
        previous_action=None,
    ):
        current_state = self.get_state(current_result, previous_state)
        action = previous_action or self.prev_action or self.choose_action(
            previous_state
        )
        reward_info = self.compute_reward(
            previous_result,
            current_result,
            previous_state,
            current_state,
        )
        updated_q = self.update(
            previous_state,
            action,
            reward_info["reward"],
            current_state,
        )

        return {
            "previous_state": previous_state.as_tuple(),
            "current_state": current_state.as_tuple(),
            "action": action,
            "reward": reward_info["reward"],
            "reason": reward_info["reason"],
            "score_delta": reward_info["score_delta"],
            "updated_q": updated_q,
        }

    def get_q(self, state):
        state_name = self._state_name(state)
        self._ensure_state(state_name)
        return dict(self.q_table[state_name])

    def q_value(self, state, action):
        state_name = self._state_name(state)
        self._ensure_state(state_name)
        return float(self.q_table[state_name].get(action, 0.0))

    def action_id(self, action):
        return self.ACTION_IDS.get(action, "PA-99")

    def is_stable_result(self, result):
        return self._case_rank(result.get("case")) == 0

    def feedback_text(self, action, feedback=None):
        if action == "POSITIVE_T":
            return self.DEFAULT_FEEDBACK["POSITIVE_T"]

        if feedback and action != self.CALL_SUPERVISOR:
            coaching = feedback.get("coaching") or []
            if coaching:
                return coaching[0]

        return self.DEFAULT_FEEDBACK.get(
            action,
            self.DEFAULT_FEEDBACK["CORRECT_POSTURE"],
        )

    def _update_one(self, state_name, action, reward, next_state_name):
        self._ensure_state(state_name)
        self._ensure_state(next_state_name)

        if action not in self.q_table[state_name]:
            self.q_table[state_name][action] = 0.0

        current_q = self.q_table[state_name][action]
        max_next_q = max(self.q_table[next_state_name].values())
        target = reward + self.gamma * max_next_q
        updated_q = current_q + self.alpha * (target - current_q)

        self.q_table[state_name][action] = float(updated_q)
        return float(updated_q)

    def _state_name_from_result(self, result):
        if self.is_stable_result(result):
            return self.STABLE_STATE

        problem_states = self._problem_state_names_from_result(result)
        if problem_states:
            return problem_states[0]

        return self.STABLE_STATE

    def _problem_state_names_from_result(self, result):
        states = []
        for item in result.get("details") or []:
            if not self._is_problem_detail(item):
                continue

            feature_index = item.get("feature_index")
            state_name = self.FEATURE_STATE_MAP.get(feature_index)
            if state_name and state_name not in states:
                states.append(state_name)

        return states

    def _is_problem_detail(self, item):
        status = item.get("status")
        if status in {"normal", "NORMAL", "정상", "?뺤긽"}:
            return False

        if item.get("risk_percent", 0.0) > 0.0:
            return True

        return self._case_rank(status) > 0

    def _ensure_state(self, state_name):
        actions = self._actions_for_state(state_name)
        for action in actions:
            self.q_table[state_name].setdefault(action, 0.0)

    def _actions_for_state(self, state_name):
        return tuple(
            self.state_actions.get(
                state_name,
                ("CORRECT_POSTURE", self.CALL_SUPERVISOR),
            )
        )

    @staticmethod
    def _state_name(state):
        if isinstance(state, PoseQState):
            return state.name
        if isinstance(state, str):
            return state
        if isinstance(state, tuple):
            return state[0]
        raise TypeError(f"Unsupported state type: {type(state)!r}")

    @staticmethod
    def _case_rank(posture_case):
        ranks = {
            "stable": 0,
            "GOOD": 0,
            "STABLE": 0,
            "안정": 0,
            "warning": 1,
            "WARNING": 1,
            "주의": 1,
            "risky": 2,
            "RISKY": 2,
            "위험": 2,
        }
        return ranks.get(posture_case, 1)

    def _case_reward(self, previous_case, current_case):
        previous_rank = self._case_rank(previous_case)
        current_rank = self._case_rank(current_case)

        if current_rank < previous_rank:
            return 0.25
        if current_rank > previous_rank:
            return -0.25
        return 0.0

    @staticmethod
    def _reward_reason(score_delta, reward):
        if reward > 0:
            return f"posture improved by {score_delta:.2f} score points"
        if reward < 0:
            return f"posture worsened by {abs(score_delta):.2f} score points"
        return "posture stayed similar"
