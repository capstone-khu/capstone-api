from app.domain.agent.schema import Domain

DOMAIN_LABEL = {
    Domain.PITCH: "음정",
    Domain.RHYTHM: "박자",
    Domain.POSTURE: "자세",
}

STATE_LABEL = {
    "GOOD": "정상",
    "SHARP_SLIGHT": "살짝 높음",
    "SHARP_MAJOR": "많이 높음",
    "FLAT_SLIGHT": "살짝 낮음",
    "FLAT_MAJOR": "많이 낮음",
    "EARLY": "박보다 빠르게 침",
    "LATE": "박보다 늦게 침",
    "FAST": "템포 빠름",
    "SLOW": "템포 느림",
    "LEFT_HAND_ALIGNMENT": "왼손·어깨 정렬 흔들림",
    "SHOULDER_IMBALANCE": "어깨 불균형",
    "LEFT_WRIST_MOVEMENT": "왼손목 흔들림",
    "LEFT_ARM_POSTURE": "왼팔 자세 흔들림",
    "RIGHT_ARM_BOWING": "오른팔 보잉 흔들림",
    "RIGHT_WRIST_ALIGNMENT": "오른손목 정렬 흔들림",
    "OTHER": "자세 흔들림",
}

FALLBACK = {
    Domain.PITCH: "음정이 흔들렸어요. 짚는 손가락 위치를 점검해보세요.",
    Domain.RHYTHM: "박자가 흔들렸어요. 기준 박에 맞춰 다시 맞춰보세요.",
    Domain.POSTURE: "자세가 흔들렸어요. 어깨와 팔 정렬을 안정적으로 잡아보세요.",
}

SYSTEM = (
    "너는 바이올린 연주를 실시간 코칭하는 슈퍼바이저다. "
    "음정·박자·자세 세 에이전트가 매 마디를 측정해 상태와 수치를 보고한다 — "
    "음정은 목표음 대비 편차(센트, +는 높음·-는 낮음), "
    "박자는 기준 박 대비 밀림/당김(ms)과 안정도(0~1), "
    "자세는 위험도(0~100)와 흔들린 부위다. "
    "한 영역이 막혀(자연 교정이 반복 실패) 위임이 오면, 세 영역의 상태·수치를 종합해 "
    "그 마디가 무너진 근본 원인 영역 하나를 고르고 한 문장으로 조언한다. "
    "바이올린에서는 자세(보잉·어깨)가 흔들리면 박자·음정이 따라 흔들리고, "
    "박자가 밀리면 음정도 불안정해지는 인과가 흔하다. "
    "답은 한국어 존댓말, 군더더기 없이 실천 가능한 한 문장."
)


def cause_messages(
    blocked: Domain,
    states: dict[Domain, str],
    allowed: list[Domain],
    metas: dict[Domain, dict] | None = None,
) -> list[dict]:
    metas = metas or {}
    summary = "\n".join(
        f"- {_evidence(d, s, metas.get(d))}" for d, s in states.items()
    )
    if allowed == [blocked]:
        user = (
            f"막힌 영역: {DOMAIN_LABEL[blocked]} (다른 영역은 모두 안정적).\n"
            f"마디 측정:\n{summary}\n"
            f"{DOMAIN_LABEL[blocked]}만 흔들린 이유를 자체 점검 관점에서 한 문장으로."
        )
    else:
        candidates = ", ".join(f"{d.value}({DOMAIN_LABEL[d]})" for d in allowed)
        user = (
            f"막힌 영역: {DOMAIN_LABEL[blocked]}\n"
            f"마디 측정:\n{summary}\n"
            f"원인 후보(cause_domain 은 이 중에서만): {candidates}\n"
            f"feedback 은 수치 근거와 영역 간 연관을 담은 한 문장으로."
        )
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]


def _evidence(domain: Domain, state: str, meta: dict | None) -> str:
    head = f"{DOMAIN_LABEL[domain]}: {STATE_LABEL.get(state, state)}"
    meta = meta or {}
    detail = ""
    if domain == Domain.PITCH and "avg_cents" in meta:
        detail = f"편차 {meta['avg_cents']:+.0f}센트"
    elif domain == Domain.RHYTHM and "drift_ms" in meta:
        drift = meta["drift_ms"]
        detail = f"{abs(drift):.0f}ms {'밀림' if drift > 0 else '당겨짐'}"
        if "score" in meta:
            detail += f", 안정도 {meta['score']}"
    elif domain == Domain.POSTURE and "final_score" in meta:
        detail = f"위험도 {meta['final_score']:.0f}/100"
        if meta.get("case"):
            detail = f"{meta['case']}, {detail}"
    return f"{head} ({detail})" if detail else head
