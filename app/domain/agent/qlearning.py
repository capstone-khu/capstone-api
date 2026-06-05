from app.domain.agent.policy import (
    DELEGATION_SUFFIX,
    REWARD_GOOD,
    REWARD_NO_CHANGE,
    REWARD_PARTIAL,
    REWARD_SUPERVISOR_HIT,
    REWARD_SUPERVISOR_MISS,
    REWARD_WORSE,
    Policy,
)
from app.domain.agent.schema import ActionSpec, AgentOutput, MeasureReading

ALPHA = 0.1
GAMMA = 0.9


class QLearningEngine:
    """마디별 측정(state) → 결정론적 action 선택 → 전이 reward → Q 갱신.

    q: (state, action) -> [q_value, update_count]. 한 도메인·한 유저의 Q 메모리 뷰.
    탐험(epsilon)은 끈다 — 배치·서빙은 argmax 결정론.
    """

    def __init__(self, policy: Policy, q: dict[tuple[str, str], list[float]]) -> None:
        self.policy = policy
        self.q = q
        self.updated: set[tuple[str, str]] = set()
        self._prev_state: str | None = None
        self._prev_action: ActionSpec | None = None

    def run(self, readings: list[MeasureReading]) -> list[AgentOutput]:
        outputs: list[AgentOutput] = []
        prev_state: str | None = None
        prev_action: ActionSpec | None = None

        for reading in sorted(readings, key=lambda r: r.measure_index):
            if not reading.valid:
                continue

            state = reading.state
            action = self._best_action(state)

            reward: float | None = None
            if prev_state is not None and prev_action is not None:
                reward = self._reward(prev_state, prev_action, state)
                self._update(prev_state, prev_action.action, reward, state)

            outputs.append(
                AgentOutput(
                    domain=self.policy.domain,
                    measure_index=reading.measure_index,
                    state=state,
                    action_id=action.action_id,
                    action=action.action,
                    feedback=action.feedback,
                    reward=reward,
                    q=round(self._get(state, action.action), 3),
                    cause_domain=None,
                    meta=reading.meta or None,
                )
            )
            prev_state, prev_action = state, action

        return outputs

    def step(self, reading: MeasureReading) -> AgentOutput | None:
        """실시간용 — 마디 1개 측정을 받아 직전 마디와의 전이로 Q 갱신.

        run() 한 바퀴분과 같지만 prev 상태를 인스턴스에 들고 마디마다 호출한다.
        측정이 무효면(프레임 부족 등) 건너뛰고 None(전이도 보존).
        """
        if not reading.valid:
            return None

        state = reading.state
        action = self._best_action(state)

        reward: float | None = None
        if self._prev_state is not None and self._prev_action is not None:
            reward = self._reward(self._prev_state, self._prev_action, state)
            self._update(self._prev_state, self._prev_action.action, reward, state)

        output = AgentOutput(
            domain=self.policy.domain,
            measure_index=reading.measure_index,
            state=state,
            action_id=action.action_id,
            action=action.action,
            feedback=action.feedback,
            reward=reward,
            q=round(self._get(state, action.action), 3),
            cause_domain=None,
            meta=reading.meta or None,
        )
        self._prev_state, self._prev_action = state, action
        return output

    def _best_action(self, state: str) -> ActionSpec:
        actions = self.policy.available_actions(state)
        return max(actions, key=lambda a: self._get(state, a.action))

    def _reward(self, prev: str, prev_action: ActionSpec, curr: str) -> float:
        was_delegation = prev_action.action_id.endswith(DELEGATION_SUFFIX)
        if self.policy.is_good(curr):
            return REWARD_SUPERVISOR_HIT if was_delegation else REWARD_GOOD

        prev_sev = self.policy.severity(prev)
        curr_sev = self.policy.severity(curr)
        if curr_sev > prev_sev:
            return REWARD_WORSE
        if curr_sev < prev_sev and self.policy.same_group(prev, curr):
            return REWARD_PARTIAL
        return REWARD_SUPERVISOR_MISS if was_delegation else REWARD_NO_CHANGE

    def _update(self, state: str, action: str, reward: float, next_state: str) -> None:
        current = self._get(state, action)
        max_next = self._max_q(next_state)
        new_value = current + ALPHA * (reward + GAMMA * max_next - current)
        cell = self.q.setdefault((state, action), [0.0, 0])
        cell[0] = new_value
        cell[1] += 1
        self.updated.add((state, action))

    def _max_q(self, state: str) -> float:
        actions = self.policy.available_actions(state)
        if not actions:
            return 0.0
        return max(self._get(state, a.action) for a in actions)

    def _get(self, state: str, action: str) -> float:
        cell = self.q.get((state, action))
        return cell[0] if cell else 0.0
