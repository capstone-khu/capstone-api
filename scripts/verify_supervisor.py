"""슈퍼바이저 원인 분석(resolve_cause)이 명세대로 작동하는 지 확인하는 스크립트.

LLM 을 임의로 주입해 키 없이 분기를 점검하고,
키가 있으면 실제 한 번 호출해서 잘 동작하는지 체크한다.

- 규칙: ① 나머지 두 영역 모두 GOOD → 원인=self,
        ② NON-GOOD 영역 → LLM이 둘 중 더 큰 영향을 주는 영역을 선택,
        ③ LLM이 허용집합 밖 도메인을 반환 → self 로 전환,
        ④ LLM None(키 없음/오류) → self degrade.
- 실호출: OPENAI_API_KEY 있으면 NON-GOOD 영역/self 원인 출력 확인 후 실제 호출.

실행: uv run python scripts/verify_supervisor.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PITCH_LOW = {"avg_cents": -118.0}
RHYTHM_LATE = {"drift_ms": 205.0, "score": 0.22}


async def _rules() -> bool:
    from app.common import llm
    from app.domain.agent.realtime import prompts
    from app.domain.agent.realtime import supervisor as sup
    from app.domain.agent.schema import Domain

    ok = True
    pitch_blocked_peer = {
        Domain.PITCH: "FLAT_MAJOR",
        Domain.RHYTHM: "LATE",
        Domain.POSTURE: "GOOD",
    }
    pitch_blocked_alone = {
        Domain.PITCH: "FLAT_MAJOR",
        Domain.RHYTHM: "GOOD",
        Domain.POSTURE: "GOOD",
    }

    def mark(label: str, passed: bool) -> None:
        nonlocal ok
        ok &= passed
        print(f"  {label}: {'OK' if passed else 'FAIL'}")

    async def fake_text(messages, schema, **kw):
        if schema is not sup.CauseText:
            raise AssertionError("self 분기는 CauseText 여야 함")
        return sup.CauseText(feedback="음정만 흔들렸어요.")

    llm.structured = fake_text
    cause, _ = await sup.resolve_cause(Domain.PITCH, pitch_blocked_alone)
    mark(f"① 동료 전원 GOOD → self (cause={cause})", cause == "pitch")

    async def fake_pick(messages, schema, **kw):
        return sup.CauseChoice(cause_domain="rhythm", feedback="박자가 밀렸어요.")

    llm.structured = fake_pick
    cause, _ = await sup.resolve_cause(Domain.PITCH, pitch_blocked_peer)
    mark(f"② 비-GOOD 동료 → LLM 선택 (cause={cause})", cause == "rhythm")

    async def fake_outside(messages, schema, **kw):
        return sup.CauseChoice(cause_domain="posture", feedback="x")  # 후보 아님

    llm.structured = fake_outside
    cause, _ = await sup.resolve_cause(Domain.PITCH, pitch_blocked_peer)
    mark(f"③ 허용집합 밖 → self 교정 (cause={cause})", cause == "pitch")

    async def fake_none(messages, schema, **kw):
        return None

    rhythm_blocked_alone = {
        Domain.PITCH: "GOOD",
        Domain.RHYTHM: "LATE",
        Domain.POSTURE: "GOOD",
    }
    llm.structured = fake_none
    cause, fb = await sup.resolve_cause(Domain.RHYTHM, rhythm_blocked_alone)
    mark(
        f"④ LLM None → degrade (cause={cause})",
        cause == "rhythm" and fb == prompts.FALLBACK[Domain.RHYTHM],
    )

    return ok


async def _live() -> bool | None:
    from app.common.config import settings

    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-...":
        print("  [skip] OPENAI_API_KEY 없음 — 실호출 생략")
        return None

    import importlib

    from app.common import llm
    from app.domain.agent.realtime import supervisor as sup
    from app.domain.agent.schema import Domain

    importlib.reload(llm)  # 규칙 단계에서 가짜로 바꾼 structured 복원
    importlib.reload(sup)

    cause, fb = await sup.resolve_cause(
        Domain.PITCH,
        {Domain.PITCH: "FLAT_MAJOR", Domain.RHYTHM: "LATE", Domain.POSTURE: "GOOD"},
        {Domain.PITCH: PITCH_LOW, Domain.RHYTHM: RHYTHM_LATE},
    )
    print(f"  peer 실호출 → cause={cause}\n    {fb}")
    ok = cause in {"rhythm", "pitch"}
    cause2, fb2 = await sup.resolve_cause(
        Domain.RHYTHM,
        {Domain.PITCH: "GOOD", Domain.RHYTHM: "SLOW", Domain.POSTURE: "GOOD"},
        {Domain.RHYTHM: {"drift_ms": -30.0, "score": 0.5}},
    )
    print(f"  self 실호출 → cause={cause2}\n    {fb2}")
    ok &= cause2 == "rhythm"
    return ok


async def main() -> int:
    results: dict[str, bool | None] = {}

    print("\n[규칙]")
    results["rules"] = await _rules()

    print("\n[실호출]")
    results["live"] = await _live()

    print("\n=== 요약 ===")
    failed = False
    for name, res in results.items():
        label = "PASS" if res else ("SKIP" if res is None else "FAIL")
        failed |= res is False
        print(f"  {name:8} {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
