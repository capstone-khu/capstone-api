from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent.pitch.measurer import PitchMeasurer
from app.domain.agent.pitch.policy import PitchPolicy
from app.domain.agent.policy import Policy
from app.domain.agent.posture.measurer import PoseMeasurer, PostureSpec
from app.domain.agent.posture.policy import PosturePolicy
from app.domain.agent.qlearning import QLearningEngine
from app.domain.agent.repository import AgentRepository
from app.domain.agent.rhythm.measurer import RhythmMeasurer, RhythmSpec
from app.domain.agent.rhythm.policy import RhythmPolicy
from app.domain.agent.schema import AgentOutput, Domain
from app.domain.agent.score import load_timed_score
from app.domain.song.model import Song


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
        score = await self._load_score(domain, song_id)
        readings = measurer.measure(recording_path, score)

        q = await self._load_q(user_id, domain)
        engine = QLearningEngine(policy, q)
        outputs = engine.run(readings)

        await self.repo.insert_feedback_events(session_id, outputs)
        await self.repo.upsert_q_values(user_id, self._changed_entries(domain, engine))
        await self.session.commit()
        return outputs

    def _for_domain(
        self, domain: Domain
    ) -> tuple[PitchMeasurer | RhythmMeasurer | PoseMeasurer, Policy]:
        if domain == Domain.PITCH:
            return PitchMeasurer(), PitchPolicy()
        if domain == Domain.RHYTHM:
            return RhythmMeasurer(), RhythmPolicy()
        if domain == Domain.POSTURE:
            return PoseMeasurer(), PosturePolicy()
        raise ValueError(f"아직 지원하지 않는 도메인입니다: {domain}")

    async def _load_score(self, domain: Domain, song_id: int):
        if domain == Domain.PITCH:
            return load_timed_score(song_id)
        if domain == Domain.RHYTHM:
            return await self._load_rhythm_spec(song_id)
        if domain == Domain.POSTURE:
            return PostureSpec(windows=load_timed_score(song_id).measure_windows())
        raise ValueError(f"아직 지원하지 않는 도메인입니다: {domain}")

    async def _load_rhythm_spec(self, song_id: int) -> RhythmSpec:
        song = await self.session.get(Song, song_id)
        if song is None:
            raise ValueError(f"존재하지 않는 곡입니다: song_id={song_id}")
        beats_per_measure = int(song.time_signature.split("/")[0])
        return RhythmSpec(
            bpm=song.bpm,
            beats_per_measure=beats_per_measure,
            total_measures=song.total_measures,
        )

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
