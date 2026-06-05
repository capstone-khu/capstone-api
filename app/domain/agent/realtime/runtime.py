from dataclasses import dataclass, field
from typing import Protocol

from app.domain.agent.qlearning import QLearningEngine
from app.domain.agent.schema import AgentOutput, Domain, MeasureReading

KIND_AUDIO = 0x01
KIND_VIDEO = 0x02

_ORDER = (Domain.PITCH, Domain.RHYTHM, Domain.POSTURE)


class Aggregator(Protocol):
    """도메인 별 스트리밍 집계 (마디 단위)"""

    domain: Domain

    def feed(self, ts_ms: int, payload: bytes) -> None: ...

    def reading(self, measure_index: int) -> MeasureReading: ...


@dataclass
class LiveSession:
    """연주 한 건의 실시간 상태"""

    session_id: int
    user_id: int
    song_id: int
    windows: list[tuple[int, float, float]]
    engines: dict[Domain, QLearningEngine]
    aggregators: dict[Domain, Aggregator]
    outputs: list[AgentOutput] = field(default_factory=list)
    completed: bool = False

    def feed(self, kind: int, ts_ms: int, payload: bytes) -> None:
        if kind == KIND_AUDIO:
            self.aggregators[Domain.PITCH].feed(ts_ms, payload)
            self.aggregators[Domain.RHYTHM].feed(ts_ms, payload)
        elif kind == KIND_VIDEO:
            self.aggregators[Domain.POSTURE].feed(ts_ms, payload)

    def score_measure(self, measure_index: int) -> list[AgentOutput]:
        produced: list[AgentOutput] = []
        for domain in _ORDER:
            reading = self.aggregators[domain].reading(measure_index)
            output = self.engines[domain].step(reading)
            if output is not None:
                produced.append(output)
                self.outputs.append(output)
        return produced

    def resolve_output(
        self, measure_index: int, domain: Domain, cause_domain: str, feedback: str
    ) -> None:
        for output in self.outputs:
            if output.measure_index == measure_index and output.domain == domain:
                output.cause_domain = cause_domain
                output.feedback = feedback
                return

    def close(self) -> None:
        closer = getattr(self.aggregators.get(Domain.POSTURE), "close", None)
        if callable(closer):
            closer()

    def changed_q(self) -> list[dict]:
        entries: list[dict] = []
        for domain, engine in self.engines.items():
            for state, action in sorted(engine.updated):
                cell = engine.q[(state, action)]
                entries.append(
                    {
                        "domain": domain.value,
                        "state": state,
                        "action": action,
                        "q_value": cell[0],
                        "update_count": cell[1],
                    }
                )
        return entries
