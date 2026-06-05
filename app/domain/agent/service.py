from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent.pitch.measurer import PitchMeasurer
from app.domain.agent.pitch.policy import PitchPolicy
from app.domain.agent.policy import Policy
from app.domain.agent.qlearning import QLearningEngine
from app.domain.agent.repository import AgentRepository
from app.domain.agent.schema import AgentOutput, Domain
from app.domain.agent.score import load_timed_score


class AgentBatchService:
    """녹음 파일 한 건을 마디별로 채점해 feedback_events·q_table_entries 에 적재.

    score 로드 → 측정 → Q 로드 → QLearningEngine → 영속(insert·upsert·commit).
    공개 엔드포인트는 없고(내부 호출·검증 스크립트 전용) 실시간 WS 는 Phase 4.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AgentRepository(session)

    async def run(
        self,
        session_id: int,
        user_id: int,
        song_id: int,
        recording_path: str,
        domain: Domain = Domain.PITCH,
    ) -> list[AgentOutput]:
        measurer, policy = self._for_domain(domain)
        score = load_timed_score(song_id)
        readings = measurer.measure(recording_path, score)

        q = await self._load_q(user_id, domain)
        engine = QLearningEngine(policy, q)
        outputs = engine.run(readings)

        await self.repo.insert_feedback_events(session_id, outputs)
        await self.repo.upsert_q_values(user_id, self._changed_entries(domain, engine))
        await self.session.commit()
        return outputs

    def _for_domain(self, domain: Domain) -> tuple[PitchMeasurer, Policy]:
        if domain == Domain.PITCH:
            return PitchMeasurer(), PitchPolicy()
        raise ValueError(f"아직 지원하지 않는 도메인입니다: {domain}")

    async def _load_q(
        self, user_id: int, domain: Domain
    ) -> dict[tuple[str, str], list[float]]:
        entries = await self.repo.load_q_table(user_id)
        return {
            (e.state, e.action): [e.q_value, e.update_count]
            for e in entries
            if e.domain == domain.value
        }

    def _changed_entries(self, domain: Domain, engine: QLearningEngine) -> list[dict]:
        return [
            {
                "domain": domain.value,
                "state": state,
                "action": action,
                "q_value": engine.q[(state, action)][0],
                "update_count": engine.q[(state, action)][1],
            }
            for (state, action) in sorted(engine.updated)
        ]
