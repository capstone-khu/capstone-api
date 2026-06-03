# State / Action 명세 (도메인별)

실제 분석 툴(`prototypes/`)에 맞춘 도메인별 State·Action·action_id·피드백 정의.

## 공통 규칙


| 항목        | 내용                                                                                                                 |
| --------- | ------------------------------------------------------------------------------------------------------------------ |
| 학습        | Q-learning `Q(S,A) ← Q(S,A) + α[R + γ·maxQ(S',A') − Q(S,A)]` (α=0.1, γ=0.9)                                        |
| 분석 단위     | 마디 1개. 도메인당 마디별 state 1개 → action 1개                                                                               |
| 위임        | GOOD이 아닌 각 state의 액션에 `CALL_SUPERVISOR`(초기 Q=0)를 함께 둔다. Q값이 가장 큰 액션을 고르되, 동점이면 교정액션 먼저(교정액션 Q가 0 밑으로 내려가야 위임이 선택됨). 위임이 선택되면 슈퍼바이저가 막힌 도메인 슬롯에 **원인 1개**를 설명한다(§4) — 동료에게 슬롯을 넘기지 않는다. |
| 기록 범위     | 마디마다 모든 도메인 출력을 `feedback_events`에 저장(GOOD/POSITIVE 포함, (measure, domain)당 최대 1행).                                 |
| 출력 형식     | `{agent, measure, state, action_id, action, feedback, reward, q, meta}`                                            |
| action_id | 도메인 프리픽스 `PT`/`RH`/`PS` + `-00` 위임 · `-01` POSITIVE · `-02+` 교정                                                    |
| `-00` 피드백 | 고정 문구 아님 — 슈퍼바이저가 산출한 **원인 설명**(비-GOOD 동료 있으면 LLM, 동료 전원 GOOD이면 룰베이스 휴리스틱). 분석 대기 중엔 "원인 분석 중"(§4). |
| `-01` 피드백 | 세 도메인 동일 — "잘 하고 있습니다. 계속 유지하세요"                                                                                   |


### Reward (세 도메인 공통)


| 상태 변화                  | reward |
| ---------------------- | ------ |
| GOOD 전환                | +1.0   |
| 부분 개선(심각→경미)           | +0.5   |
| 변화 없음                  | −0.3   |
| 악화                     | −0.8   |
| 위임(CALL_SUPERVISOR) 적중 | +0.8   |
| 위임 무효                  | −0.5   |


부분개선/악화는 각 도메인 **심각도 순서**로 판정한다 .

- pitch: GOOD < SLIGHT < MAJOR 
- rhythm: GOOD < FAST·SLOW < EARLY·LATE 
- posture: GOOD < CAUTION < RISK. `score_delta`는 reward가 아니라 **meta로 보존**(/coach 참고용).

---

## 1. 음정 (pitch) — `agent: "pitch"`

`SwiftF0` cents 편차로 분류.

### State


| State        | 설명    | 조건(cents)  |
| ------------ | ----- | ---------- |
| GOOD         | 정상    | −30 ~ +30  |
| SHARP_SLIGHT | 약간 높음 | +30 ~ +100 |
| SHARP_MAJOR  | 많이 높음 | ≥ +100     |
| FLAT_SLIGHT  | 약간 낮음 | −30 ~ −100 |
| FLAT_MAJOR   | 많이 낮음 | ≤ −100     |


### Action


| action_id | action          | feedback                               | 발동 state                   |
| --------- | --------------- | -------------------------------------- | -------------------------- |
| PT-00     | CALL_SUPERVISOR | 슈퍼바이저 산출 원인 설명(LLM/휴리스틱, §4)         | GOOD 외 모든 state            |
| PT-01     | POSITIVE_PITCH  | 잘 하고 있습니다. 계속 유지하세요                    | GOOD                       |
| PT-02     | PITCH_UP        | 음정을 올리세요                               | FLAT_SLIGHT / FLAT_MAJOR   |
| PT-03     | PITCH_DOWN      | 음정을 내리세요                               | SHARP_SLIGHT / SHARP_MAJOR |


### 마디 집계

50ms 프레임의 cents를 마디 단위로 모아 평균 → 마디당 state 1개.

---

## 2. 박자 (rhythm) — `agent: "rhythm"`

`madmom`의 drift(ms)·score·beat 비율로 분류.

### State


| State | 설명    | 조건                              |
| ----- | ----- | ------------------------------- |
| GOOD  | 정상    | score ≥ 0.80, drift −80 ~ +80ms |
| EARLY | 일찍 연주 | drift < −80ms                   |
| LATE  | 늦게 연주 | drift > +80ms                   |
| FAST  | 템포 빠름 | beat 과다(beat/onset > 1.3)       |
| SLOW  | 템포 느림 | 그 외                             |


### Action


| action_id | action          | feedback                               | 발동 state        |
| --------- | --------------- | -------------------------------------- | --------------- |
| RH-00     | CALL_SUPERVISOR | 슈퍼바이저 산출 원인 설명(LLM/휴리스틱, §4)         | GOOD 외 모든 state |
| RH-01     | POSITIVE_RHYTHM | 잘 하고 있습니다. 계속 유지하세요                    | GOOD            |
| RH-02     | RHYTHM_WAIT     | 박자보다 일찍 연주하고 있습니다. 박자를 맞추세요            | EARLY           |
| RH-03     | RHYTHM_CATCH_UP | 박자보다 늦게 연주하고 있습니다. 박자를 맞추세요            | LATE            |
| RH-04     | TEMPO_SLOW_DOWN | 템포가 빠릅니다. 속도를 늦추세요                     | FAST            |
| RH-05     | TEMPO_SPEED_UP  | 템포가 느립니다. 속도를 높이세요                     | SLOW            |


### 마디 집계

반 마디(2박) 전/후반을 대표 state 하나로 합쳐 마디당 state 1개.

---

## 3. 자세 (posture) — `agent: "posture"`

`MediaPipe` 6개 피처 → `pose_model.pkl`→ case/final_score 로 분류.

### State


| State                 | 설명            | 조건          |
| --------------------- | ------------- | ----------- |
| GOOD                  | 정상            | case = GOOD |
| LEFT_HAND_ALIGNMENT   | 왼손-왼어깨 거리 불안정 | 특징0 위험      |
| SHOULDER_IMBALANCE    | 양 어깨 높이 차     | 특징1 위험      |
| LEFT_WRIST_MOVEMENT   | 왼손목 과도한 움직임   | 특징2 위험      |
| LEFT_ARM_POSTURE      | 왼팔 각도 불안정     | 특징3 위험      |
| RIGHT_ARM_BOWING      | 오른팔 보잉 각도 무너짐 | 특징4 위험      |
| RIGHT_WRIST_ALIGNMENT | 오른손목 정렬 흐트러짐  | 특징5 위험      |


### Action


| action_id | action                 | feedback                               | 발동 state              |
| --------- | ---------------------- | -------------------------------------- | --------------------- |
| PS-00     | CALL_SUPERVISOR        | 슈퍼바이저 산출 원인 설명(LLM/휴리스틱, §4)         | GOOD 외 모든 state       |
| PS-01     | POSITIVE_POSTURE       | 잘 하고 있습니다. 계속 유지하세요                    | GOOD                  |
| PS-02     | HAND_ALIGNMENT_CORRECT | 왼손과 어깨 사이 거리를 안정적으로 유지하세요.             | LEFT_HAND_ALIGNMENT   |
| PS-03     | SHOULDER_BALANCE       | 양쪽 어깨 높이를 균형 있게 맞추세요.                  | SHOULDER_IMBALANCE    |
| PS-04     | WRIST_STRAIGHTEN       | 왼손목 움직임을 줄이고 중심을 안정적으로 잡으세요.           | LEFT_WRIST_MOVEMENT   |
| PS-05     | ARM_POSTURE_CORRECT    | 왼팔 각도를 안정적으로 유지하세요.                    | LEFT_ARM_POSTURE      |
| PS-06     | ARM_STRAIGHTEN         | 오른팔 보잉 각도를 자연스럽게 펴세요.                  | RIGHT_ARM_BOWING      |
| PS-07     | WRIST_ALIGNMENT        | 오른손목을 세우고 보잉 방향을 안정적으로 유지하세요.          | RIGHT_WRIST_ALIGNMENT |
| PS-99     | CORRECT_POSTURE        | 자세를 안정적으로 교정하세요.                       | 그 외 분류 안 되는 경우        |


### 마디 집계

영상 프레임을 measure_index 기준으로 마디별로 묶음 → 마디당 state 1개.

---

## 4. 슈퍼바이저 원인 분석 (위임 처리)

도메인 D에서 `CALL_SUPERVISOR`(-00)가 선택되면, 막힌 도메인 슬롯을 **삭제하지 않고** 그 자리에
**원인 1개**를 설명한다. 동료에게 슬롯을 넘기지 않으며, 나머지 도메인은 각자 item을 그대로 낸다.

- **Branch A — 비-GOOD 동료 ≥ 1 (LLM):** 다른 두 도메인의 `{state, action, meta}`를 LLM(OpenAI)에 전달해
  주원인 1개와 설명을 생성한다. 실시간 핫 루프를 막지 않도록 **비동기 보강**으로 처리한다 — 먼저 D 슬롯에
  "원인 분석 중"(`cause.pending=true`)을 보내고, LLM 결과가 오면 `feedback_update`로 교체한다(`cause.source="llm"`).
- **Branch B — 동료 둘 다 GOOD (룰베이스 휴리스틱):** LLM 없이 아래 매핑으로 원인 1개를 즉시 채운다
  (`cause.source="heuristic"`).

각 도메인 meta는 원인 분석 입력이다(예: rhythm `drift_label`·`score`, posture `feature`·`risk_percent`,
pitch `avg_cents`·`state`).

### 휴리스틱 매핑 (Branch B 전용)

> **바이올린 교습 직관**에 기반한다 — 음정·박자 문제의 근본 원인은 대개 **자세(셋업)** 이고,
> 그 안에서 **왼손 자세 ↔ 음정**, **활 잡은 오른팔 자세 ↔ 박자** 가 짝을 이룬다. 그래서
> ① 음정이 막히면 → 왼손 자세, ② 박자가 막히면 → 오른팔(활) 자세를 원인으로 가리킨다.
> 반대로 ③ 자세가 막혔는데 음정·박자가 멀쩡하면, 그 자세 부위에 맞는 감각
> (왼손부 → 음정, 오른팔부 → 박자)을 지렛대로 가리킨다. 메시지는 다른 피드백처럼 **한 문장**으로
> 짧게 통일한다(전문용어 '보잉' 등은 쓰지 않음). (운영하며 조정 가능)

| 막힌 도메인 | state | 원인 도메인 | 메시지 |
| --- | --- | --- | --- |
| pitch | FLAT_SLIGHT / FLAT_MAJOR | posture | 왼손 자세를 바로잡으면 음정이 올라와요. |
| pitch | SHARP_SLIGHT / SHARP_MAJOR | posture | 어깨와 왼손 힘을 빼면 음정이 잡혀요. |
| rhythm | EARLY / LATE | posture | 활 자세를 안정시키면 박자가 맞아요. |
| rhythm | FAST / SLOW | posture | 오른팔 힘을 빼면 템포가 안정돼요. |
| posture | LEFT_HAND_ALIGNMENT / LEFT_WRIST_MOVEMENT / LEFT_ARM_POSTURE / SHOULDER_IMBALANCE | pitch | 왼손으로 음 짚기에 집중하면 자세가 풀려요. |
| posture | RIGHT_ARM_BOWING / RIGHT_WRIST_ALIGNMENT | rhythm | 박자에 맞춰 활을 그으면 자세가 안정돼요. |
| posture | (그 외 / PS-99) | rhythm | 박자에 맞춰 천천히 활을 그어보세요. |