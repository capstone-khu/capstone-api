# API 명세

캡스톤 백엔드 REST API 명세.

## 공통 규칙

- 모든 응답은 공통 봉투 `ApiResponse` 로 감싼다. `null` 필드는 직렬화에서 제외된다.
  ```json
  { "success": true, "status": 200, "message": "...", "data": {}, "code": null, "meta": null }
  ```
- 인증이 필요한 엔드포인트는 `Authorization: Bearer <JWT>` 헤더를 요구한다.
- 실패 응답은 `code`(에러 코드) 와 `meta`(path·timestamp) 를 포함한다.
- 모든 datetime 필드는 **KST(Asia/Seoul) ISO 8601**(`+09:00`)로 직렬화한다. `meta.timestamp` 는 epoch millis(타임존 무관).
- 미디어(합성 영상 등) URL은 FastAPI `StaticFiles` 로 서빙하는 **같은 오리진 상대 경로**(`/media/...`)다. env `MEDIA_BASE_URL` 설정 시 절대 URL로 직렬화될 수 있다.

### 에러 코드

| Code | Status | Message |
|---|---|---|
| COM_400_001 | 400 | 매핑할 수 없는 값입니다. (요청 본문 검증 실패) |
| COM_401_001 | 401 | 인증이 필요합니다. (토큰 누락·만료·무효) |
| COM_404_001 | 404 | 존재하지 않는 리소스입니다. |
| COM_500_001 | 500 | 서버 내부 오류가 발생했습니다. |
| AUT_401_001 | 401 | 이름 또는 비밀번호가 올바르지 않습니다. |
| SON_404_001 | 404 | 존재하지 않는 곡입니다. |
| SON_404_002 | 404 | 존재하지 않는 마디입니다. |
| SES_400_001 | 400 | 협주 상대 녹음이 올바르지 않습니다. |
| SES_403_001 | 403 | 본인의 세션이 아닙니다. |
| SES_404_001 | 404 | 존재하지 않는 세션입니다. |
| SES_409_001 | 409 | 이미 종료된 세션입니다. |
| SES_409_002 | 409 | 완료되지 않은 세션입니다. |
| SES_503_001 | 503 | AI 분석 생성에 실패했습니다. 잠시 후 다시 시도해주세요. |
| REC_404_001 | 404 | 존재하지 않는 녹음입니다. |
| DUE_403_001 | 403 | 본인의 협주 영상이 아닙니다. |
| DUE_404_001 | 404 | 존재하지 않는 협주 영상입니다. |

---

# 0. 헬스체크 (operational)

> 운영용 엔드포인트다. `ApiResponse`로 감싸지 않고 단순 JSON을 반환한다.

## 0.1 Liveness

**1. API 설명**
프로세스가 살아 있는지 확인한다. 의존성(DB 등)은 검사하지 않는다.

**2. Endpoint + Method**
`GET /health`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
(없음)

**6. Request Body**
(없음)

**7. Request Example**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| status | string | Y | 프로세스 상태 | "ok" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{ "status": "ok" }
```

**10. Error Response Example (4xx, 5xx)**
(없음 — 프로세스가 떠 있는 한 항상 200)

## 0.2 Readiness

**1. API 설명**
트래픽을 받을 준비가 됐는지 확인한다. DB 연결(`SELECT 1`)까지 검사하며, 실패 시 `503` 을 반환한다.

**2. Endpoint + Method**
`GET /health/ready`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
(없음)

**6. Request Body**
(없음)

**7. Request Example**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| status | string | Y | 준비 상태(ready/not ready) | "ready" |
| db | string | Y | DB 연결 상태(up/down) | "up" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{ "status": "ready", "db": "up" }
```

**10. Error Response Example (4xx, 5xx)**
`503 Service Unavailable`
```json
{ "status": "not ready", "db": "down" }
```

---

# 1. 인증 (auth)

## 1.1 로그인

**1. API 설명**
이름과 비밀번호로 로그인하고 JWT 액세스 토큰을 발급한다.

**2. Endpoint + Method**
`POST /auth/login`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Content-Type | string | Y | 요청 본문 형식 | application/json |

**6. Request Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| name | string | Y | 사용자 이름(로그인 ID) | "김서연" |
| password | string | Y | 비밀번호 | "pw1234" |

**7. Request Example (JSON)**
```json
{ "name": "김서연", "password": "pw1234" }
```

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| access_token | string | Y | JWT 액세스 토큰 | "eyJhbGciOi..." |
| token_type | string | Y | 토큰 타입 | "bearer" |
| user.id | number | Y | 사용자 ID | 1 |
| user.name | string | Y | 사용자 이름 | "김서연" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1Ni␣...",
    "token_type": "bearer",
    "user": { "id": 1, "name": "김서연" }
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`400 Bad Request`
```json
{
  "success": false,
  "status": 400,
  "message": "매핑할 수 없는 값입니다.",
  "code": "COM_400_001",
  "meta": { "path": "/auth/login", "timestamp": 1733132400000 }
}
```
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "이름 또는 비밀번호가 올바르지 않습니다.",
  "code": "AUT_401_001",
  "meta": { "path": "/auth/login", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/auth/login", "timestamp": 1733132400000 }
}
```

---

# 2. 사용자 / 마이페이지 (user)

## 2.1 내 프로필 조회

**1. API 설명**
현재 로그인한 사용자의 프로필을 조회한다.

**2. Endpoint + Method**
`GET /me`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| id | number | Y | 사용자 ID | 1 |
| name | string | Y | 사용자 이름 | "김서연" |
| created_at | string(datetime) | Y | 가입 시각(ISO 8601) | "2026-06-01T10:00:00+09:00" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": { "id": 1, "name": "김서연", "created_at": "2026-06-01T10:00:00+09:00" }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/me", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/me", "timestamp": 1733132400000 }
}
```

---

## 2.2 연주 이력 조회

**1. API 설명**
내 연주 이력을 페이지 단위(기본 3개)로 조회한다. 각 항목은 영역별 **문제 개수**(`state != GOOD`) 통계와 **집중 반복 필요 마디**(`focus_measures`)를 포함하며, 협주 기록은 합성 영상 ID와 협주 상대 이름(`partner_name`)을 함께 반환해 카드에 "협주 · {이름}" 배지를 자족적으로 그릴 수 있게 한다. (`feedback_events` 엔 GOOD도 저장되지만 stats는 문제만 센다 — DESIGN #25) `focus_measures` 가 비어있지 않으면 그 세션에 "집중 반복 레슨" 버튼을 노출하고, 각 마디 데이터는 §4.6 마디 상세 조회를 재사용한다(DESIGN #28). 목록은 `played_at` 내림차순(최신순)으로 정렬한다.

**2. Endpoint + Method**
`GET /me/history`

**3. Path Parameter**
(없음)

**4. Query Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| page | number | N | 페이지 번호(1-based, 기본 1) | 1 |
| size | number | N | 페이지당 개수(기본 3) | 3 |

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| page | number | Y | 현재 페이지 | 1 |
| size | number | Y | 페이지당 개수 | 3 |
| total | number | Y | 전체 이력 수 | 7 |
| items | array | Y | 이력 목록 | [] |
| items[].session_id | number | Y | 세션 ID | 12 |
| items[].song_id | number | Y | 곡 ID | 1 |
| items[].song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| items[].played_at | string(datetime) | Y | 연주 시각 | "2026-06-02T09:30:00+09:00" |
| items[].mode | string | Y | 모드(solo/duet) | "duet" |
| items[].stats.pitch | number | Y | 음정 문제 개수(GOOD 제외) | 3 |
| items[].stats.rhythm | number | Y | 박자 문제 개수(GOOD 제외) | 1 |
| items[].stats.posture | number | Y | 자세 문제 개수(GOOD 제외) | 2 |
| items[].focus_measures | array | Y | 집중 반복 필요 마디(세 영역 모두 `state != GOOD`인 마디). 없으면 `[]` | [5, 7] |
| items[].duet_composite_id | number | N | 협주 합성 영상 ID(협주 기록만) | 5 |
| items[].partner_name | string | N | 협주 상대 이름(협주 기록만) | "이준호" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "page": 1, "size": 3, "total": 7,
    "items": [
      { "session_id": 12, "song_id": 1, "song_title": "반짝 반짝 작은별", "played_at": "2026-06-02T09:30:00+09:00",
        "mode": "duet", "stats": { "pitch": 3, "rhythm": 1, "posture": 2 }, "focus_measures": [5, 7], "duet_composite_id": 5, "partner_name": "이준호" },
      { "session_id": 10, "song_id": 1, "song_title": "반짝 반짝 작은별", "played_at": "2026-06-01T18:10:00+09:00",
        "mode": "solo", "stats": { "pitch": 0, "rhythm": 2, "posture": 1 }, "focus_measures": [] }
    ]
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/me/history", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/me/history", "timestamp": 1733132400000 }
}
```

---

## 2.3 협주 합성 영상 단건 조회

**1. API 설명**
협주 합성 영상 1건의 상태를 조회한다. `POST /sessions/{id}/complete` 가 돌려준 `duet_composite_id` 로 합성 잡 진행 상태(`pending → processing → ready/failed`)를 폴링하는 용도다. (합성 잡 = DESIGN #38 `BackgroundTasks`+ffmpeg)

**2. Endpoint + Method**
`GET /duet-videos/{duet_composite_id}`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| duet_composite_id | number | Y | 합성 영상 ID | 5 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| duet_composite_id | number | Y | 합성 영상 ID | 5 |
| song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| partner_name | string | Y | 협주 상대 이름 | "이준호" |
| status | string | Y | 합성 상태(pending/processing/ready/failed) | "ready" |
| composite_video_url | string | N | 합성 영상 URL(ready 시) | "/media/duet/5.mp4" |
| created_at | string(datetime) | Y | 생성 시각 | "2026-06-02T09:35:00+09:00" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "duet_composite_id": 5, "song_title": "반짝 반짝 작은별", "partner_name": "이준호",
    "status": "processing", "created_at": "2026-06-02T09:35:00+09:00"
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/duet-videos/5", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 협주 영상이 아닙니다.",
  "code": "DUE_403_001",
  "meta": { "path": "/duet-videos/5", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 협주 영상입니다.",
  "code": "DUE_404_001",
  "meta": { "path": "/duet-videos/999", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/duet-videos/5", "timestamp": 1733132400000 }
}
```

---

# 3. 곡 / 악보 (song)

## 3.1 곡 목록 조회

**1. API 설명**
연주 가능한 곡 목록을 조회한다.

**2. Endpoint + Method**
`GET /songs`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| total | number | Y | 전체 곡 수 | 1 |
| songs | array | Y | 곡 목록 | [] |
| songs[].id | number | Y | 곡 ID | 1 |
| songs[].number | number | Y | 곡 번호 | 1 |
| songs[].title | string | Y | 곡명 | "반짝 반짝 작은별" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": { "total": 1, "songs": [ { "id": 1, "number": 1, "title": "반짝 반짝 작은별" } ] }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/songs", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/songs", "timestamp": 1733132400000 }
}
```

---

## 3.2 악보 조회

**1. API 설명**
한 곡의 악보를 마디·음표·가사 단위로 조회한다.

**2. Endpoint + Method**
`GET /songs/{song_id}/score`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song_id | number | Y | 곡 ID | 1 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song.id | number | Y | 곡 ID | 1 |
| song.number | number | Y | 곡 번호 | 1 |
| song.title | string | Y | 곡명 | "반짝 반짝 작은별" |
| song.bpm | number | Y | 기본 템포 | 96 |
| song.time_signature | string | Y | 박자표 | "4/4" |
| song.total_measures | number | Y | 전체 마디 수 | 24 |
| measures | array | Y | 마디 목록 | [] |
| measures[].measure_index | number | Y | 마디 번호(1-based) | 1 |
| measures[].notes | array | Y | 음표 배열 | [] |
| measures[].notes[].pitch | string | Y | 음높이 | "C4" |
| measures[].notes[].duration | string | Y | 음길이 | "quarter" |
| measures[].notes[].position | number | Y | 마디 내 박 위치 | 0 |
| measures[].notes[].lyric | string | N | 가사 음절 | "반" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "song": { "id": 1, "number": 1, "title": "반짝 반짝 작은별", "bpm": 96, "time_signature": "4/4", "total_measures": 24 },
    "measures": [
      { "measure_index": 1, "notes": [
        { "pitch": "C4", "duration": "quarter", "position": 0, "lyric": "반" },
        { "pitch": "C4", "duration": "quarter", "position": 1, "lyric": "짝" }
      ] }
    ]
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/songs/1/score", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 곡입니다.",
  "code": "SON_404_001",
  "meta": { "path": "/songs/999/score", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/songs/1/score", "timestamp": 1733132400000 }
}
```

---

## 3.3 협주 상대 목록 조회

**1. API 설명**
해당 곡으로 녹음이 있는 다른 연주자(협주 상대) 목록을 조회한다. 요청자 본인의 녹음은 제외한다.

**2. Endpoint + Method**
`GET /songs/{song_id}/duet-partners`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song_id | number | Y | 곡 ID | 1 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song_title | string | Y | 곡명(헤더 표시용) | "반짝 반짝 작은별" |
| partners | array | Y | 협주 상대 목록(없으면 빈 배열) | [] |
| partners[].recording_id | number | Y | 협주에 사용할 녹음 ID | 8 |
| partners[].user_name | string | Y | 연주자 이름 | "이준호" |
| partners[].recorded_at | string(datetime) | Y | 녹음 시각 | "2026-05-30T12:00:00+09:00" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "song_title": "반짝 반짝 작은별",
    "partners": [
      { "recording_id": 8, "user_name": "이준호", "recorded_at": "2026-05-30T12:00:00+09:00" }
    ]
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/songs/1/duet-partners", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 곡입니다.",
  "code": "SON_404_001",
  "meta": { "path": "/songs/999/duet-partners", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/songs/1/duet-partners", "timestamp": 1733132400000 }
}
```

---

# 4. 연주 세션 (session)

## 4.1 세션 생성

**1. API 설명**
연주 세션을 생성한다. `mode` 가 `duet` 이면 `partner_recording_id` 가 필요하다. 협주 녹음은 **존재**해야 하고(없으면 404 `REC_404_001`), **요청 곡(`song_id`)의 녹음**이며 **요청자 본인의 녹음이 아니어야** 한다(어긋나면 400 `SES_400_001`). 응답은 연주 화면 자족용으로 곡명(`song_title`)을 포함하며, `duet` 이면 협주 상대 이름(`partner_name`)과 라이브 재생용 음원 URL(`audio_url`)도 함께 반환해 "협주 · {상대} 음원 재생 중"을 자족적으로 그릴 수 있게 한다(상대 음원은 소리만 재생, 영상은 미노출 — DESIGN #37).

**2. Endpoint + Method**
`POST /sessions`

**3. Path Parameter**
(없음)

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |
| Content-Type | string | Y | 요청 본문 형식 | application/json |

**6. Request Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song_id | number | Y | 곡 ID | 1 |
| mode | string | Y | 연주 모드(solo/duet) | "duet" |
| partner_recording_id | number | N | 협주 상대 녹음 ID(duet 시 필수) | 8 |

**7. Request Example (JSON)**
```json
{ "song_id": 1, "mode": "duet", "partner_recording_id": 8 }
```

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 생성된 세션 ID | 12 |
| status | string | Y | 세션 상태 | "created" |
| song_title | string | Y | 곡명(연주 화면 헤더 표시용) | "반짝 반짝 작은별" |
| partner_name | string | N | 협주 상대 이름(duet만) | "손수민" |
| audio_url | string | N | 협주 상대 음원 URL(duet만, 라이브 재생용·오디오 트랙) | "/media/recordings/1.mp4" |

**9. Success Response Example (2xx)**
`201 Created`
```json
{
  "success": true,
  "status": 201,
  "message": "리소스가 생성되었습니다.",
  "data": { "session_id": 12, "status": "created", "song_title": "반짝 반짝 작은별", "partner_name": "손수민", "audio_url": "/media/recordings/1.mp4" }
}
```

**10. Error Response Example (4xx, 5xx)**
`400 Bad Request`
```json
{
  "success": false,
  "status": 400,
  "message": "매핑할 수 없는 값입니다.",
  "code": "COM_400_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```
```json
{
  "success": false,
  "status": 400,
  "message": "협주 상대 녹음이 올바르지 않습니다.",
  "code": "SES_400_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 곡입니다.",
  "code": "SON_404_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 녹음입니다.",
  "code": "REC_404_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions", "timestamp": 1733132400000 }
}
```

---

## 4.2 실시간 피드백 스트림 (WebSocket)

**1. API 설명**
연주 중 마디마다 **측정 입력(마이크 오디오·카메라 프레임)** 을 보내면, 백엔드가 직접 측정(`SwiftF0`/`madmom`/`MediaPipe`)해 도메인별 state를 만들고 멀티에이전트가 피드백을 돌려주는 WebSocket 채널. 측정·분석·피드백·보상 모두 마디 1개 단위이며 백엔드에서 처리한다. 연결 전제: 세션 생성(REST) → 권한 허용·카운트인(클라) 완료 후 연결.

> **세션 생명주기(DESIGN #8·#9):** WS 연결 시 세션이 `in_progress` 가 된다. 진행 중 WS가 비정상으로 끊기면 서버는 세션을 **즉시 `aborted`** 처리한다(재접속·이어가기 없음). 따라서 **정상 종료는 WS를 닫기 전에 `POST /complete` 를 먼저 호출**해야 한다(status→`completed`, 이후 close는 무효 처리). 진행 중 끊김 = 그 연주 폐기(녹화본 업로드 불가). 실시간 동안 만든 피드백·Q는 메모리에만 있다가 `/complete` 시 일괄 영속된다(DESIGN #10).

**2. Endpoint + Method**
`WS /sessions/{session_id}/stream` (WebSocket Upgrade)

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |

**4. Query Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| token | string | N | 헤더 사용 불가 클라이언트용 JWT(쿼리 전달) | "eyJhbGciOi..." |

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | N | Bearer 액세스 토큰(쿼리 token 미사용 시) | Bearer eyJhbGciOi... |

**6. Request Body** (client → server 메시지)
측정 입력을 두 종류로 보낸다. 오디오·영상 바이트는 **바이너리 프레임**으로 계속 스트리밍하고, 한 마디가 끝날 때마다 **measure JSON 메시지**로 마디 경계를 알린다. state·분석은 백엔드가 측정해 만든다.

**바이너리 프레임** (오디오·영상) — `[ kind(1) | ts_ms(4) | payload ]`

| 필드 | 크기 | 설명 |
|---|---|---|
| kind | 1 byte | `0x01`=오디오, `0x02`=영상 |
| ts_ms | 4 byte | 카운트인 종료(t0) 기준 경과 시간(ms), uint32 **big-endian**. 단조 증가해야 하며 역행·동일 값 프레임은 폐기될 수 있다 |
| payload | N byte | 오디오=PCM16 LE (48kHz mono, 100ms=4,800샘플·9,600byte 단위) · 영상=JPEG (10~15fps) |

> 마디 ↔ 오디오/영상 매칭은 별도 식별자 없이 각 프레임의 `ts_ms` 로 처리한다.

**measure 메시지** (마디 경계, JSON)

| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| type | string | Y | 메시지 타입 | "measure" |
| measure_index | number | Y | 현재 마디 (**1-based**, 곡 악보 마디 번호와 일치) | 12 |

> 한 마디의 오디오·영상 프레임을 **모두 보낸 뒤** measure 메시지를 보낸다. 순서가 뒤집히면 그 마디 구간이 비어 분석이 누락된다.

**7. Request Example**
바이너리 프레임:
```
[ 0x01 | ts_ms(uint32 BE) | PCM16 bytes ]   # 오디오 100ms
[ 0x02 | ts_ms(uint32 BE) | JPEG bytes  ]   # 영상 프레임
```
measure 메시지(JSON):
```json
{ "type": "measure", "measure_index": 12 }
```

**8. Response Body** (server → client 메시지)
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| type | string | Y | 메시지 타입(`feedback` / `feedback_update`) | "feedback" |
| measure_index | number | Y | 현재 마디 | 12 |
| items | array | Y | 도메인별 피드백(reward 낮은 영역 먼저, 동률 자세 우선) | [] |
| items[].domain | string | Y | 영역(pitch/rhythm/posture) | "pitch" |
| items[].action_id | string | Y | 액션 ID. `-00`=위임(원인 분석) · `-01`=POSITIVE(GOOD 격려) · `-02+`=교정 | "PT-03" |
| items[].action | string | Y | 액션명 | "PITCH_DOWN" |
| items[].feedback | string | Y | 피드백 문구(위임 시 원인 설명, 분석 중이면 "원인 분석 중") | "음정을 내리세요" |
| items[].cause | object | N | 위임(`-00`) 시 원인 분석 정보. 없으면 생략 | null |
| items[].cause.pending | boolean | N | 원인 분석 중(LLM 대기). true면 `feedback`="원인 분석 중", `domain` 없음 | true |
| items[].cause.domain | string | N | 지목된 원인 영역(pitch/rhythm/posture). 막힌 도메인 자신(self)일 수 있음. pending 중엔 없음 | "rhythm" |

> GOOD 도메인은 `action_id=-01`(POSITIVE) item으로 실시간 격려를 보낸다(WS 전달 + `feedback_events` 에도 기록 — DESIGN #25).
> 위임(`-00`) 마디에선 막힌 도메인 item을 **삭제하지 않고** 그 슬롯에 원인 설명을 담는다(DESIGN #21). 위임은 **모두 LLM 원인 분석**을 거친다(단일 경로): 먼저 `cause.pending=true`(`feedback`="원인 분석 중")로 보낸 뒤 LLM 결과가 오면 `feedback_update` 메시지로 그 item을 교체한다. 비-GOOD 동료가 있으면 그 동료 또는 막힌 도메인 자신이 원인으로 지목될 수 있고, **동료가 모두 GOOD이면 외부 원인이 없으므로 `cause.domain`은 막힌 도메인 자신(self)으로 고정**된다(LLM은 설명 텍스트만 생성). 나머지 도메인은 각자 item(GOOD→POSITIVE, 비-GOOD→교정)을 그대로 보낸다.
> `feedback_update`(server→client) 메시지: `{ "type": "feedback_update", "measure_index": <n>, "item": { ...교체할 도메인 item... } }`. 같은 `measure_index`·`item.domain`의 기존 item을 교체한다(비동기 LLM 원인 분석 결과 도착 시).

**9. Success Response Example (2xx)**
`101 Switching Protocols` (WebSocket 연결 수립 후 메시지 교환)

위임 + LLM 원인 분석 (음정이 막힘, 비-GOOD 동료 있음 → 로딩 먼저):
```json
{
  "type": "feedback",
  "measure_index": 12,
  "items": [
    { "domain": "pitch", "action_id": "PT-00", "action": "CALL_SUPERVISOR", "feedback": "원인 분석 중", "cause": { "pending": true } },
    { "domain": "rhythm", "action_id": "RH-03", "action": "RHYTHM_CATCH_UP", "feedback": "박자보다 늦게 연주하고 있습니다. 박자를 맞추세요" },
    { "domain": "posture", "action_id": "PS-01", "action": "POSITIVE_POSTURE", "feedback": "잘 하고 있습니다. 계속 유지하세요" }
  ]
}
```

이어서 LLM 결과 도착 → 음정 item 교체:
```json
{
  "type": "feedback_update",
  "measure_index": 12,
  "item": { "domain": "pitch", "action_id": "PT-00", "action": "CALL_SUPERVISOR", "feedback": "박자가 밀리면서 음정도 같이 내려간 것 같아요.", "cause": { "pending": false, "domain": "rhythm" } }
}
```

전부 GOOD (도메인마다 POSITIVE 격려):
```json
{
  "type": "feedback",
  "measure_index": 8,
  "items": [
    { "domain": "pitch", "action_id": "PT-01", "action": "POSITIVE_PITCH", "feedback": "잘 하고 있습니다. 계속 유지하세요" },
    { "domain": "rhythm", "action_id": "RH-01", "action": "POSITIVE_RHYTHM", "feedback": "잘 하고 있습니다. 계속 유지하세요" },
    { "domain": "posture", "action_id": "PS-01", "action": "POSITIVE_POSTURE", "feedback": "잘 하고 있습니다. 계속 유지하세요" }
  ]
}
```

위임 + 동료 전원 GOOD → 막힌 도메인 자신이 원인(self) (외부 원인 없음). 음정 슬롯은 위 첫 예시처럼 `cause.pending=true`를 먼저 보낸 뒤, LLM 결과가 오면 self 원인으로 교체:
```json
{
  "type": "feedback_update",
  "measure_index": 15,
  "item": { "domain": "pitch", "action_id": "PT-00", "action": "CALL_SUPERVISOR", "feedback": "자세·박자는 안정적인데 음정만 흔들려요. 첫 음 짚는 손가락 위치를 점검해보세요.", "cause": { "pending": false, "domain": "pitch" } }
}
```

**10. Error Response Example (4xx, 5xx)**
연결 거부/종료는 WebSocket close code 로 전달한다.
`4401` (인증 실패 — 연결 수립 전 HTTP 401 후 거부)
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/stream", "timestamp": 1733132400000 }
}
```
`4404` (close) — 존재하지 않는 세션
```json
{ "type": "error", "code": "SES_404_001", "message": "존재하지 않는 세션입니다." }
```
`1011` (close) — 서버 내부 오류
```json
{ "type": "error", "code": "COM_500_001", "message": "서버 내부 오류가 발생했습니다." }
```

---

## 4.3 세션 종료

**1. API 설명**
연주를 정상 종료하며 녹음(오디오)·녹화(영상) 파일을 함께 업로드한다. 파일은 EC2 로컬 볼륨에 저장(`StaticFiles` `/media/` 서빙)하고 DB엔 경로만 기록하며, 협주였으면 좌우 분할 합성 영상 잡을 트리거한다(`hstack`+`amix`, mp4). WS 스트림은 state만 전달하므로 실제 미디어 바이트는 이 요청의 `multipart/form-data` 로 전송한다. **이때 실시간 동안 메모리에 모은 `feedback_events` 를 일괄 insert 하고 Q테이블을 upsert 한다(DESIGN #10)** — WS close 전에 이 요청을 먼저 보내야 세션이 `completed` 로 확정된다(DESIGN #9).

**2. Endpoint + Method**
`POST /sessions/{session_id}/complete`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |
| Content-Type | string | Y | 멀티파트 폼 | multipart/form-data |

**6. Request Body** (`multipart/form-data`)
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| audio | file | Y | 녹음 오디오 파일(원본 포맷 그대로) | recording.webm |
| video | file | Y | 녹화 영상 파일(원본 포맷 그대로) | recording.webm |

**7. Request Example**
```
POST /sessions/12/complete
Content-Type: multipart/form-data; boundary=----X

------X
Content-Disposition: form-data; name="audio"; filename="recording.webm"
Content-Type: audio/webm
<binary>
------X
Content-Disposition: form-data; name="video"; filename="recording.webm"
Content-Type: video/webm
<binary>
------X--
```

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |
| recording_id | number | Y | 저장된 녹음 ID | 21 |
| duet_composite_id | number | N | 협주 합성 영상 ID(협주만, 잡 대기) | 5 |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": { "session_id": 12, "recording_id": 21, "duet_composite_id": 5 }
}
```

**10. Error Response Example (4xx, 5xx)**
`400 Bad Request`
```json
{
  "success": false,
  "status": 400,
  "message": "매핑할 수 없는 값입니다.",
  "code": "COM_400_001",
  "meta": { "path": "/sessions/12/complete", "timestamp": 1733132400000 }
}
```
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/complete", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/complete", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/complete", "timestamp": 1733132400000 }
}
```
`409 Conflict`
```json
{
  "success": false,
  "status": 409,
  "message": "이미 종료된 세션입니다.",
  "code": "SES_409_001",
  "meta": { "path": "/sessions/12/complete", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/complete", "timestamp": 1733132400000 }
}
```

---

## 4.4 세션 중도 종료

**1. API 설명**
연주를 중도 종료한다. 이번 연주는 저장하지 않고 세션을 `aborted` 처리한다. 메모리에 모인 `feedback_events`·Q 갱신·녹화본 **모두 폐기**(미저장)한다(DESIGN #10). 진행 중 WS 비정상 끊김도 서버가 동일하게 `aborted` 로 처리한다(DESIGN #9).

**2. Endpoint + Method**
`POST /sessions/{session_id}/abort`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
(없음)

**9. Success Response Example (2xx)**
`200 OK`
```json
{ "success": true, "status": 200, "message": "요청에 성공했습니다." }
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/abort", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/abort", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/abort", "timestamp": 1733132400000 }
}
```
`409 Conflict`
```json
{
  "success": false,
  "status": 409,
  "message": "이미 종료된 세션입니다.",
  "code": "SES_409_001",
  "meta": { "path": "/sessions/12/abort", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/abort", "timestamp": 1733132400000 }
}
```

---

## 4.5 결과 조회

**1. API 설명**
세션의 마디별 누적 마킹을 조회한다. 이번 세션(채움)과 같은 user×song 의 모드 무관 직전 완료 세션(외곽선)을 함께 반환한다. 마킹은 **문제 마디만**(`state != GOOD`) 표시한다 — `feedback_events` 엔 GOOD도 저장되지만 결과 화면은 문제 위주다(DESIGN #25). **완료(`completed`)된 세션만 조회할 수 있다** — 그 외 상태(`created`/`in_progress`/`aborted`)면 `409`(SES_409_002)를 반환한다.

**2. Endpoint + Method**
`GET /sessions/{session_id}/result`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |
| song_id | number | Y | 곡 ID | 1 |
| song_title | string | Y | 곡명(헤더 표시용) | "반짝 반짝 작은별" |
| played_at | string(datetime) | Y | 연주 시각(헤더 표시용) | "2026-06-02T09:30:00+09:00" |
| mode | string | Y | 모드 | "duet" |
| partner_name | string | N | 협주 상대 이름(duet만) | "이준호" |
| measures | array | Y | 마디별 마킹 | [] |
| measures[].measure_index | number | Y | 마디 번호 | 1 |
| measures[].current | array | Y | 이번 세션 마킹(채움) | [] |
| measures[].current[].domain | string | Y | 영역 | "pitch" |
| measures[].current[].action_id | string | Y | 액션 ID(`-00`=위임 원인 → 무지개, `-02+`=교정) | "PT-03" |
| measures[].current[].feedback | string | Y | 피드백(도메인당 1개) | "음정을 내리세요" |
| measures[].previous | array | Y | 직전 세션 마킹(외곽선) | [] |
| measures[].previous[].domain | string | Y | 영역 | "rhythm" |
| measures[].previous[].action_id | string | Y | 액션 ID | "RH-03" |
| measures[].previous[].feedback | string | Y | 피드백(도메인당 1개) | "박자보다 늦게 연주하고 있습니다" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "session_id": 12, "song_id": 1, "song_title": "반짝 반짝 작은별", "played_at": "2026-06-02T09:30:00+09:00", "mode": "duet", "partner_name": "이준호",
    "measures": [
      { "measure_index": 1,
        "current": [ { "domain": "pitch", "action_id": "PT-03", "feedback": "음정을 내리세요" } ],
        "previous": [ { "domain": "rhythm", "action_id": "RH-03", "feedback": "박자보다 늦게 연주하고 있습니다" } ] }
    ]
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/result", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/result", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/result", "timestamp": 1733132400000 }
}
```
`409 Conflict` — 완료되지 않은 세션
```json
{
  "success": false,
  "status": 409,
  "message": "완료되지 않은 세션입니다.",
  "code": "SES_409_002",
  "meta": { "path": "/sessions/12/result", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/result", "timestamp": 1733132400000 }
}
```

---

## 4.6 마디 상세 조회

**1. API 설명**
결과 화면의 마디 상세 모달 데이터(큰 악보 + 이번/이전 세션 마킹)를 조회한다. 곡에 존재하지 않는 `measure_index` 면 `404`(SON_404_002)를 반환한다.

**2. Endpoint + Method**
`GET /sessions/{session_id}/measures/{measure_index}`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |
| measure_index | number | Y | 마디 번호 | 1 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| measure_index | number | Y | 마디 번호 | 1 |
| notes | array | Y | 음표 배열(필드는 §3.2 악보 조회와 동일) | [] |
| notes[].pitch | string | Y | 음높이 | "C4" |
| notes[].duration | string | Y | 음길이 | "quarter" |
| notes[].position | number | Y | 마디 내 박 위치 | 0 |
| notes[].lyric | string | N | 가사 음절 | "반" |
| current_markings | array | Y | 이번 세션 마킹 | [] |
| current_markings[].domain | string | Y | 영역 | "pitch" |
| current_markings[].action_id | string | Y | 액션 ID(`-00`=위임 원인 → 무지개, `-02+`=교정) | "PT-03" |
| current_markings[].feedback | string | Y | 피드백(도메인당 1개) | "음정을 내리세요" |
| previous_markings | array | Y | 이전 세션 마킹(참고) | [] |
| previous_markings[].domain | string | Y | 영역 | "rhythm" |
| previous_markings[].action_id | string | Y | 액션 ID | "RH-03" |
| previous_markings[].feedback | string | Y | 피드백(도메인당 1개) | "박자보다 늦게 연주하고 있습니다" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "measure_index": 1,
    "notes": [ { "pitch": "C4", "duration": "quarter", "position": 0, "lyric": "반" } ],
    "current_markings": [ { "domain": "pitch", "action_id": "PT-03", "feedback": "음정을 내리세요" } ],
    "previous_markings": []
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/measures/1", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/measures/1", "timestamp": 1733132400000 }
}
```
`404 Not Found` — 존재하지 않는 세션
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/measures/1", "timestamp": 1733132400000 }
}
```
`404 Not Found` — 곡에 없는 마디
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 마디입니다.",
  "code": "SON_404_002",
  "meta": { "path": "/sessions/12/measures/999", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/measures/1", "timestamp": 1733132400000 }
}
```

---

## 4.7 AI 상세 분석 조회

**1. API 설명**
세션의 AI 상세 분석(디브리핑 + 영역별 수준·진단·연습)을 조회한다. 없으면 첫 호출에서 `/coach` LLM(OpenAI)으로 **동기 생성**(수 초 블로킹)한 뒤 캐시하며, 이후 같은 세션은 저장본을 반환한다. (백그라운드 잡 아님 — DESIGN #31) 세 영역이 모두 무너진 마디(`focus_measures`)도 함께 반환해 '집중 반복 레슨' 진입에 쓴다(`feedback_events` 에서 도출, 캐시 대상 아님 — DESIGN #28). **완료(`completed`)된 세션만 조회할 수 있다** — 그 외 상태면 `409`(SES_409_002)를 반환한다. LLM 생성에 실패하면 **저장 없이** `503`(SES_503_001)을 반환하며, 다음 호출에서 다시 생성을 시도한다.

**2. Endpoint + Method**
`GET /sessions/{session_id}/analysis`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 세션 ID | 12 |
| headline | string | Y | 한 줄 헤드라인 | "이번엔 음정이 제일 아쉬웠어요" |
| coach_comment | string | Y | 코치 코멘트(디브리핑) | "음정이 자주 흔들렸어요..." |
| domains.pitch.level | string | Y | 음정 수준(good/ok/weak) | "weak" |
| domains.pitch.diagnosis | string | Y | 음정 진단 | "높은 음에서 음정이 올라갔어요" |
| domains.pitch.practice | string | N | 음정 연습 처방(good이면 없음) | "스케일을 천천히..." |
| domains.rhythm | object | Y | 박자 분석(동일 구조) | {} |
| domains.posture | object | Y | 자세 분석(동일 구조) | {} |
| focus_measures | array | Y | 세 영역 모두 `state != GOOD`인 마디(집중 반복 레슨용). 없으면 `[]` | [5, 7] |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "session_id": 12,
    "headline": "이번엔 음정이 제일 아쉬웠어요",
    "coach_comment": "음정이 자주 흔들렸고, 자세가 무너질 때 음정도 같이 흔들렸어요.",
    "domains": {
      "pitch": { "level": "weak", "diagnosis": "높은 음에서 음정이 올라갔어요", "practice": "스케일을 천천히 반복해보세요" },
      "rhythm": { "level": "ok", "diagnosis": "일부 구간에서 살짝 늦었어요", "practice": "메트로놈에 맞춰 연습해보세요" },
      "posture": { "level": "good", "diagnosis": "자세는 안정적이었어요" }
    },
    "focus_measures": [5, 7]
  }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/analysis", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/analysis", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/analysis", "timestamp": 1733132400000 }
}
```
`409 Conflict` — 완료되지 않은 세션
```json
{
  "success": false,
  "status": 409,
  "message": "완료되지 않은 세션입니다.",
  "code": "SES_409_002",
  "meta": { "path": "/sessions/12/analysis", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/analysis", "timestamp": 1733132400000 }
}
```
`503 Service Unavailable` — LLM 생성 실패(미저장, 재호출 시 재시도)
```json
{
  "success": false,
  "status": 503,
  "message": "AI 분석 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
  "code": "SES_503_001",
  "meta": { "path": "/sessions/12/analysis", "timestamp": 1733132400000 }
}
```

---

## 4.8 직전 세션 마킹 조회

**1. API 설명**
연주(라이브) 화면이 시작될 때, **직전 완료 세션의 마디별 마킹(외곽선)** 을 한 번에 미리 받아오는 용도다. 연주 화면은 이번 세션 마킹을 WS로 실시간 채우고(채움), 이 응답으로 받은 직전 세션 마킹을 외곽선으로 겹쳐 "여기서 실수했었지"를 마디 도착 전부터 보여준다(도착 시 왼쪽에 직전 피드백을 현재 피드백과 함께 표시). 직전 세션 기준은 **같은 user×song 의 모드 무관 직전 완료(completed) 세션**(DESIGN #30)이며, 마킹은 결과 화면과 동일하게 **문제 마디만**(`state != GOOD`)이다. WS 연결 전에 호출한다(외곽선을 카운트인 단계부터 그릴 수 있도록).

**2. Endpoint + Method**
`GET /sessions/{session_id}/previous-markings`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| session_id | number | Y | 이번(현재) 세션 ID | 12 |

**4. Query Parameter**
(없음)

**5. Request Header**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| Authorization | string | Y | Bearer 액세스 토큰 | Bearer eyJhbGciOi... |

**6. Request Body**
(없음)

**7. Request Example (JSON)**
(없음)

**8. Response Body**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| previous_session_id | number | N | 직전 완료 세션 ID(없으면 생략) | 10 |
| measures | array | Y | 직전 세션 마디별 마킹(문제 마디만, 없으면 빈 배열) | [] |
| measures[].measure_index | number | Y | 마디 번호 | 4 |
| measures[].markings | array | Y | 그 마디의 도메인별 마킹(도메인당 1개) | [] |
| measures[].markings[].domain | string | Y | 영역(pitch/rhythm/posture) | "pitch" |
| measures[].markings[].action_id | string | Y | 액션 ID(`-00`=위임 원인 → 무지개, `-02+`=교정) | "PT-03" |
| measures[].markings[].feedback | string | Y | 피드백(도메인당 1개) | "음정을 내리세요" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "previous_session_id": 10,
    "measures": [
      { "measure_index": 4, "markings": [
        { "domain": "pitch", "action_id": "PT-03", "feedback": "음정을 내리세요" }
      ] },
      { "measure_index": 7, "markings": [
        { "domain": "pitch", "action_id": "PT-03", "feedback": "음정을 내리세요" },
        { "domain": "rhythm", "action_id": "RH-03", "feedback": "박자보다 늦게 연주하고 있습니다" }
      ] }
    ]
  }
}
```

직전 완료 세션이 없으면(첫 연주):
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": { "measures": [] }
}
```

**10. Error Response Example (4xx, 5xx)**
`401 Unauthorized`
```json
{
  "success": false,
  "status": 401,
  "message": "인증이 필요합니다.",
  "code": "COM_401_001",
  "meta": { "path": "/sessions/12/previous-markings", "timestamp": 1733132400000 }
}
```
`403 Forbidden`
```json
{
  "success": false,
  "status": 403,
  "message": "본인의 세션이 아닙니다.",
  "code": "SES_403_001",
  "meta": { "path": "/sessions/12/previous-markings", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/previous-markings", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/sessions/12/previous-markings", "timestamp": 1733132400000 }
}
```
