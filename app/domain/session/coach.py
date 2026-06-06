from typing import Literal

from pydantic import BaseModel

from app.common import llm
from app.domain.agent.model import FeedbackEvent
from app.domain.agent.realtime.prompts import DOMAIN_LABEL, STATE_LABEL
from app.domain.agent.schema import Domain

MAX_TOKENS = 700
TIMEOUT_S = 30.0

SYSTEM = (
    "너는 바이올린 연주가 끝난 뒤 그 연주를 돌아보는 레슨 디브리핑 코치다. "
    "음정·박자·자세 세 에이전트가 마디마다 남긴 측정 기록을 읽고, "
    "사람 선생님 말투(전문용어 없는 한국어 존댓말)로 이번 연주를 정리한다.\n"
    "- headline: 가장 아쉬운 영역을 짚는 한 줄 (예: '이번엔 음정이 제일 아쉬웠어요').\n"
    "- coach_comment: 한 단락 디브리핑. 가장 자주 흔들린 영역을 짚고, "
    "위임 기록(원인 도메인)이 있으면 영역 간 연관을 한 문장으로 언급한다. "
    "직전 연주 기록이 있으면 나아진 점이나 반복된 약점도 짚는다.\n"
    "- 영역별 level: 문제가 없으면 good, 한두 마디에서 가볍게 흔들렸으면 ok, "
    "여러 마디에서 반복되거나 심하게 흔들렸으면 weak.\n"
    "- 영역별 diagnosis: 어디서(몇 마디 부근)·뭐가·왜 문제였는지 한 줄. "
    "good 이면 칭찬 한 줄.\n"
    "- 영역별 practice: ok/weak 이면 연습 이름과 방법을 담은 처방 한 줄을 "
    "반드시 채우고, good 이면 JSON null 로 비운다(문자열 'null' 금지)."
)


class DomainCoach(BaseModel):
    level: Literal["good", "ok", "weak"]
    diagnosis: str
    practice: str | None


class CoachReport(BaseModel):
    headline: str
    coach_comment: str
    pitch: DomainCoach
    rhythm: DomainCoach
    posture: DomainCoach


async def generate(
    song_title: str,
    events: list[FeedbackEvent],
    previous_events: list[FeedbackEvent],
) -> CoachReport | None:
    """세션 기록으로 AI 상세 분석 리포트를 LLM 으로 생성한다.

    events 는 이번 세션의 전체 기록(GOOD 포함), previous_events 는 직전 완료
    세션의 문제 마킹이다. 키 없음·지연·오류면 None 을 반환한다(폴백 없음).
    """
    user = f"곡: {song_title}\n\n이번 연주 마디별 기록:\n{_session_summary(events)}"
    if previous_events:
        user += f"\n\n직전 연주의 문제 마디(참고·비교용):\n{_markings_summary(previous_events)}"
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    report = await llm.structured(
        messages, CoachReport, max_tokens=MAX_TOKENS, timeout=TIMEOUT_S
    )
    return _normalize(report) if report is not None else None


def _normalize(report: CoachReport) -> CoachReport:
    for domain in (report.pitch, report.rhythm, report.posture):
        practice = (domain.practice or "").strip()
        if domain.level == "good" or practice.lower() in ("", "null", "none"):
            domain.practice = None
    return report


def _session_summary(events: list[FeedbackEvent]) -> str:
    by_measure: dict[int, list[FeedbackEvent]] = {}
    for event in events:
        by_measure.setdefault(event.measure_index, []).append(event)
    lines = []
    for measure in sorted(by_measure):
        parts = [_event_summary(e) for e in by_measure[measure]]
        lines.append(f"- 마디 {measure}: {' / '.join(parts)}")
    return "\n".join(lines) if lines else "(기록 없음)"


def _markings_summary(events: list[FeedbackEvent]) -> str:
    by_measure: dict[int, list[str]] = {}
    for event in events:
        label = DOMAIN_LABEL[Domain(event.domain)]
        state = STATE_LABEL.get(event.state, event.state)
        by_measure.setdefault(event.measure_index, []).append(f"{label} {state}")
    lines = [
        f"- 마디 {measure}: {', '.join(parts)}"
        for measure, parts in sorted(by_measure.items())
    ]
    return "\n".join(lines)


def _event_summary(event: FeedbackEvent) -> str:
    label = DOMAIN_LABEL[Domain(event.domain)]
    state = STATE_LABEL.get(event.state, event.state)
    head = f"{label} {state}"
    detail = _evidence(event)
    if detail:
        head += f"({detail})"
    if event.cause_domain is not None:
        cause = DOMAIN_LABEL.get(Domain(event.cause_domain), event.cause_domain)
        head += f" — 막혀서 원인 분석, 원인={cause}: {event.feedback}"
    return head


def _evidence(event: FeedbackEvent) -> str:
    meta = event.meta or {}
    if event.domain == Domain.PITCH and "avg_cents" in meta:
        return f"편차 {meta['avg_cents']:+.0f}센트"
    if event.domain == Domain.RHYTHM and "drift_ms" in meta:
        drift = meta["drift_ms"]
        detail = f"{abs(drift):.0f}ms {'밀림' if drift > 0 else '당겨짐'}"
        if "score" in meta:
            detail += f", 안정도 {meta['score']}"
        return detail
    if event.domain == Domain.POSTURE and "final_score" in meta:
        detail = f"위험도 {meta['final_score']:.0f}/100"
        if meta.get("case"):
            detail = f"{meta['case']}, {detail}"
        return detail
    return ""
