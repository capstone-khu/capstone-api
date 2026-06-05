from typing import Literal

from pydantic import BaseModel

from app.common import llm
from app.domain.agent.realtime import prompts
from app.domain.agent.schema import Domain


class CauseChoice(BaseModel):
    cause_domain: Literal["pitch", "rhythm", "posture"]
    feedback: str


class CauseText(BaseModel):
    feedback: str


async def resolve_cause(
    blocked: Domain,
    states: dict[Domain, str],
    metas: dict[Domain, dict] | None = None,
) -> tuple[str, str]:
    """위임된 도메인의 원인 도메인·설명을 LLM 으로 분석한다.

    states 는 도메인별 상태, metas 는 에이전트 측정 수치(편차·드리프트·위험도)로
    LLM 의 인과 판단 근거가 된다. 비-GOOD 동료가 있으면 {동료들 + 자신} 중 원인 1개
    선택, 동료 전원 GOOD 이면 self 고정(설명만). 키 없음·지연·오류면 self degrade.
    """
    non_good = [d for d, s in states.items() if d != blocked and s != "GOOD"]
    fallback = prompts.FALLBACK[blocked]

    if not non_good:
        messages = prompts.cause_messages(blocked, states, [blocked], metas)
        result = await llm.structured(messages, CauseText)
        return blocked.value, result.feedback if result else fallback

    allowed = [*non_good, blocked]
    result = await llm.structured(
        prompts.cause_messages(blocked, states, allowed, metas), CauseChoice
    )
    if result is None:
        return blocked.value, fallback
    allowed_values = {d.value for d in allowed}
    cause = (
        result.cause_domain
        if result.cause_domain in allowed_values
        else blocked.value
    )
    return cause, result.feedback
