# DB 테이블 명세

캡스톤 백엔드 MySQL 8 스키마. 설계 배경은 [`DESIGN.md`](../design/DESIGN.md) 참고.

## 공통 규칙

- 가변 엔티티는 `BaseEntity` 를 상속한다 → 공통 컬럼 `id`(PK)·`created_at`·`updated_at` 보유.
- append-only 로그(`feedback_events`)는 `updated_at` 없이 `created_at` 만 둔다.
- 문자셋 `utf8mb4`. 시각 컬럼은 `DATETIME`, **KST(Asia/Seoul) 기준 저장**.
- Key 표기: `PK`(기본키) / `FK`(외래키) / `-`(키 아님).
- 미디어 URL 컬럼(`audio_url`·`video_url`·`composite_video_url`)은 EC2 로컬 볼륨의 **`/media/` 상대 경로**를 저장한다(FastAPI `StaticFiles` 서빙). 절대 URL은 응답 직렬화 시 env `MEDIA_BASE_URL` 로 조립.

---

## 1. users

**1. 테이블 설명**
서비스 사용자. 이름 + 비밀번호로 로그인하며 이름이 로그인 ID를 겸한다.

**2. 테이블 이름**
`users`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 사용자 ID | 1 |
| - | name | VARCHAR(50) | NOT NULL, UNIQUE | 이름(로그인 ID) | "김서연" |
| - | password_hash | VARCHAR(255) | NOT NULL | 비밀번호 해시(bcrypt/argon2) | "$2b$12$..." |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-01 10:00:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-01 10:00:00" |

**4. Example Row**
```json
{
  "id": 1,
  "name": "김서연",
  "password_hash": "$2b$12$abcdef...",
  "created_at": "2026-06-01 10:00:00",
  "updated_at": "2026-06-01 10:00:00"
}
```

---

## 2. songs

**1. 테이블 설명**
연주 가능한 곡 메타데이터.

**2. 테이블 이름**
`songs`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 곡 ID | 1 |
| - | number | INT | NOT NULL | 곡 번호 | 1 |
| - | title | VARCHAR(100) | NOT NULL | 곡명 | "반짝 반짝 작은별" |
| - | bpm | INT | NOT NULL | 기본 템포(카운트인·메트로놈) | 96 |
| - | time_signature | VARCHAR(10) | NOT NULL | 박자표 | "4/4" |
| - | total_measures | INT | NOT NULL | 전체 마디 수 | 24 |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-01 10:00:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-01 10:00:00" |

**4. Example Row**
```json
{
  "id": 1,
  "number": 1,
  "title": "반짝 반짝 작은별",
  "bpm": 96,
  "time_signature": "4/4",
  "total_measures": 24,
  "created_at": "2026-06-01 10:00:00",
  "updated_at": "2026-06-01 10:00:00"
}
```

---

## 3. song_measures

**1. 테이블 설명**
곡의 마디 단위 악보. 음표·가사를 JSON 으로 보관한다. 화면 페이지(연주 4마디/페이지, 결과 6×2)는 프론트에서 계산한다.

**2. 테이블 이름**
`song_measures`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 마디 행 ID | 100 |
| FK | song_id | BIGINT | NOT NULL | 곡 ID(songs.id) | 1 |
| - | measure_index | INT | NOT NULL | 마디 번호(1-based) | 1 |
| - | notes | JSON | NOT NULL | 음표 배열 [{pitch,duration,position,lyric}] | [{"pitch":"C4","duration":"quarter","position":0,"lyric":"반"}] |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-01 10:00:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-01 10:00:00" |

> UNIQUE(song_id, measure_index)

**4. Example Row**
```json
{
  "id": 100,
  "song_id": 1,
  "measure_index": 1,
  "notes": [ { "pitch": "C4", "duration": "quarter", "position": 0, "lyric": "반" }, { "pitch": "C4", "duration": "quarter", "position": 1, "lyric": "짝" } ],
  "created_at": "2026-06-01 10:00:00",
  "updated_at": "2026-06-01 10:00:00"
}
```

---

## 4. sessions

**1. 테이블 설명**
연주 세션(혼자/협주). 집중 반복 레슨은 별도 세션 없이 `feedback_events` 에서 세션별 문제 마디(세 영역 모두 `state != GOOD`)를 도출해 처리하므로 모드에 포함하지 않는다.

**2. 테이블 이름**
`sessions`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 세션 ID | 12 |
| FK | user_id | BIGINT | NOT NULL | 연주자 ID(users.id) | 1 |
| FK | song_id | BIGINT | NOT NULL | 곡 ID(songs.id) | 1 |
| - | mode | ENUM('solo','duet') | NOT NULL | 연주 모드 | "duet" |
| FK | partner_recording_id | BIGINT | NULL | 협주 상대 녹음(recordings.id) | 8 |
| - | status | ENUM('created','in_progress','completed','aborted') | NOT NULL | 세션 상태 | "completed" |
| - | started_at | DATETIME | NULL | 연주 시작 시각 | "2026-06-02 09:30:00" |
| - | ended_at | DATETIME | NULL | 연주 종료 시각 | "2026-06-02 09:33:00" |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:29:50" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-02 09:33:00" |

**4. Example Row**
```json
{
  "id": 12,
  "user_id": 1,
  "song_id": 1,
  "mode": "duet",
  "partner_recording_id": 8,
  "status": "completed",
  "started_at": "2026-06-02 09:30:00",
  "ended_at": "2026-06-02 09:33:00",
  "created_at": "2026-06-02 09:29:50",
  "updated_at": "2026-06-02 09:33:00"
}
```

---

## 5. recordings

**1. 테이블 설명**
세션에서 생성된 녹음물(오디오·영상). `available_for_duet` 가 true면 다른 사용자의 협주 상대 목록에 노출된다.

**2. 테이블 이름**
`recordings`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 녹음 ID | 21 |
| FK | session_id | BIGINT | NOT NULL | 생성 세션(sessions.id) | 12 |
| FK | user_id | BIGINT | NOT NULL | 소유자(users.id) | 1 |
| FK | song_id | BIGINT | NOT NULL | 곡 ID(songs.id) | 1 |
| - | audio_url | VARCHAR(500) | NOT NULL | 오디오 파일 경로(업로드 원본 포맷 그대로, `/media/` 상대) | "/media/recordings/21.webm" |
| - | video_url | VARCHAR(500) | NOT NULL | 영상 파일 경로(업로드 원본 포맷 그대로, `/media/` 상대) | "/media/recordings/21.webm" |
| - | duration | INT | NOT NULL | 길이(초) | 180 |
| - | available_for_duet | BOOLEAN | NOT NULL, DEFAULT true | 협주 상대 노출 여부 | true |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:33:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-02 09:33:00" |

**4. Example Row**
```json
{
  "id": 21,
  "session_id": 12,
  "user_id": 1,
  "song_id": 1,
  "audio_url": "/media/recordings/21.webm",
  "video_url": "/media/recordings/21.webm",
  "duration": 180,
  "available_for_duet": true,
  "created_at": "2026-06-02 09:33:00",
  "updated_at": "2026-06-02 09:33:00"
}
```

---

## 6. duet_composites

**1. 테이블 설명**
협주 종료 시 내 영상과 상대 영상을 좌우 분할로 합성한 영상. 비동기 잡으로 생성되며 상태를 추적한다.

**2. 테이블 이름**
`duet_composites`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 합성 영상 ID | 5 |
| FK | session_id | BIGINT | NOT NULL | 협주 세션(sessions.id) | 12 |
| FK | my_recording_id | BIGINT | NOT NULL | 내 녹음(recordings.id) | 21 |
| FK | partner_recording_id | BIGINT | NOT NULL | 상대 녹음(recordings.id) | 8 |
| - | composite_video_url | VARCHAR(500) | NULL | 합성 영상 경로(ready 시, `/media/` 상대) | "/media/duet/5.mp4" |
| - | status | ENUM('pending','processing','ready','failed') | NOT NULL, DEFAULT 'pending' | 잡 상태 | "ready" |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:33:01" |
| - | ready_at | DATETIME | NULL | 합성 완료 시각 | "2026-06-02 09:35:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-02 09:35:00" |

**4. Example Row**
```json
{
  "id": 5,
  "session_id": 12,
  "my_recording_id": 21,
  "partner_recording_id": 8,
  "composite_video_url": "/media/duet/5.mp4",
  "status": "ready",
  "created_at": "2026-06-02 09:33:01",
  "ready_at": "2026-06-02 09:35:00",
  "updated_at": "2026-06-02 09:35:00"
}
```

---

## 7. analysis_reports

**1. 테이블 설명**
세션별 AI 상세 분석 결과. `/coach` LLM 이 1회 생성 후 캐시한다. 세션당 1개.

**2. 테이블 이름**
`analysis_reports`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 리포트 ID | 30 |
| FK | session_id | BIGINT | NOT NULL, UNIQUE | 대상 세션(sessions.id) | 12 |
| - | headline | VARCHAR(255) | NOT NULL | 한 줄 헤드라인 | "이번엔 음정이 제일 아쉬웠어요" |
| - | coach_comment | TEXT | NOT NULL | 코치 코멘트(디브리핑) | "음정이 자주 흔들렸어요..." |
| - | domains | JSON | NOT NULL | 영역별 {level,diagnosis,practice} | {"pitch":{"level":"weak","diagnosis":"...","practice":"..."}} |
| - | generated_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:34:00" |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:34:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-02 09:34:00" |

**4. Example Row**
```json
{
  "id": 30,
  "session_id": 12,
  "headline": "이번엔 음정이 제일 아쉬웠어요",
  "coach_comment": "음정이 자주 흔들렸고 자세가 무너질 때 같이 흔들렸어요.",
  "domains": { "pitch": { "level": "weak", "diagnosis": "높은 음에서 음정이 올라갔어요", "practice": "스케일을 천천히 반복" }, "rhythm": { "level": "ok", "diagnosis": "일부 구간 늦음", "practice": "메트로놈 연습" }, "posture": { "level": "good", "diagnosis": "안정적" } },
  "generated_at": "2026-06-02 09:34:00",
  "created_at": "2026-06-02 09:34:00",
  "updated_at": "2026-06-02 09:34:00"
}
```

---

## 8. q_table_entries (L1)

**1. 테이블 설명**
멀티에이전트 도메인별 Q테이블. 키는 user×domain×state×action 이며 마디(measure)는 키에 없다(마디 무관 일반화). `action` 에는 액션명(예: PITCH_DOWN) 또는 `CALL_SUPERVISOR` 가 들어간다(action_id가 아니라 액션명 저장).

**2. 테이블 이름**
`q_table_entries`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 엔트리 ID | 500 |
| FK | user_id | BIGINT | NOT NULL | 사용자(users.id) | 1 |
| - | domain | ENUM('pitch','rhythm','posture') | NOT NULL | 도메인 | "pitch" |
| - | state | VARCHAR(30) | NOT NULL | State enum(GOOD 포함) | "SHARP_MAJOR" |
| - | action | VARCHAR(40) | NOT NULL | 액션명 또는 CALL_SUPERVISOR | "PITCH_DOWN" |
| - | q_value | FLOAT | NOT NULL, DEFAULT 0 | Q값 | 0.7 |
| - | update_count | INT | NOT NULL, DEFAULT 0 | 갱신 횟수 | 5 |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-01 10:00:00" |
| - | updated_at | DATETIME | NOT NULL | 수정 시각 | "2026-06-02 09:33:00" |

> UNIQUE(user_id, domain, state, action)

**4. Example Row**
```json
{
  "id": 500,
  "user_id": 1,
  "domain": "pitch",
  "state": "SHARP_MAJOR",
  "action": "PITCH_DOWN",
  "q_value": 0.7,
  "update_count": 5,
  "created_at": "2026-06-01 10:00:00",
  "updated_at": "2026-06-02 09:33:00"
}
```

---

## 9. feedback_events (L4)

**1. 테이블 설명**
마디별 에이전트 출력 기록(append-only). **(measure_index, domain)당 최대 1행**(마디당 보통 3행). **마디마다 모든 도메인 출력을 기록**한다(GOOD/POSITIVE 포함) — 종합 피드백이 잘한 곳까지 봐야 하기 때문. 결과 마킹·이력 stats는 `state != 'GOOD'` 로 걸러 **문제만** 센다(저장은 전부, 표시는 문제 위주). 위임(`-00`)은 새 행을 만들지 않고 막힌 도메인 자신의 행에 원인 분석 결과를 담는다 — `cause_domain`(지목된 원인 영역) + `feedback`(원인 설명) + `meta.cause_source`(`llm`/`heuristic`). 세션별 집중 반복 레슨 마디는 별도 테이블 없이 이 표에서 (measure_index 별) **세 도메인이 모두 `state != 'GOOD'`** 인 마디를 조회해 도출한다. 결과·AI분석·이력 통계의 단일 소스다. 추가만 하고 수정하지 않으므로 `updated_at` 이 없다.

**2. 테이블 이름**
`feedback_events`

**3. 컬럼 명세**
| Key | Name | Type | Constraint(nullable) | Description | Example |
|---|---|---|---|---|---|
| PK | id | BIGINT | NOT NULL, AUTO_INCREMENT | 이벤트 ID | 9001 |
| FK | session_id | BIGINT | NOT NULL | 세션(sessions.id) | 12 |
| - | measure_index | INT | NOT NULL | 마디 번호(분석·피드백 단위) | 12 |
| - | domain | ENUM('pitch','rhythm','posture') | NOT NULL | 도메인 | "pitch" |
| - | state | VARCHAR(30) | NOT NULL | State enum | "SHARP_MAJOR" |
| - | action_id | VARCHAR(10) | NOT NULL | 액션 ID(PT/RH/PS-NN) | "PT-03" |
| - | action | VARCHAR(40) | NOT NULL | 액션명 | "PITCH_DOWN" |
| - | feedback | TEXT | NOT NULL | 피드백 문구 | "음정을 내리세요" |
| - | reward | FLOAT | NULL | 직전 마디 대비 보상(첫 마디 null) | 1.0 |
| - | q | FLOAT | NOT NULL | 갱신 후 Q값 | 0.7 |
| - | cause_domain | VARCHAR(10) | NULL | 위임(`-00`) 시 지목된 원인 도메인 | "rhythm" |
| - | is_fallback | BOOLEAN | NOT NULL, DEFAULT false | 원인이 룰베이스 휴리스틱(동료 전원 GOOD)인지 여부. LLM 분석이면 false | false |
| - | meta | JSON | NULL | 도메인 고유 정보(pitch=avg_cents·state, rhythm=drift_label·score, posture=feature·risk_percent). 위임 행은 `cause_source` 포함 | {} |
| - | created_at | DATETIME | NOT NULL | 생성 시각 | "2026-06-02 09:31:00" |

> INDEX(session_id, measure_index)

**4. Example Row**
```json
{
  "id": 9001,
  "session_id": 12,
  "measure_index": 12,
  "domain": "pitch",
  "state": "SHARP_MAJOR",
  "action_id": "PT-03",
  "action": "PITCH_DOWN",
  "feedback": "음정을 내리세요",
  "reward": 1.0,
  "q": 0.7,
  "cause_domain": null,
  "is_fallback": false,
  "meta": { "avg_cents": 112.0 },
  "created_at": "2026-06-02 09:31:00"
}
```
