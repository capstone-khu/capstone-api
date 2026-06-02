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
| SES_403_001 | 403 | 본인의 세션이 아닙니다. |
| SES_404_001 | 404 | 존재하지 않는 세션입니다. |
| SES_409_001 | 409 | 이미 종료된 세션입니다. |
| REC_404_001 | 404 | 존재하지 않는 녹음입니다. |
| PRG_404_001 | 404 | 추천된 집중 레슨이 아닙니다. |
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

## 1.2 로그아웃

**1. API 설명**
로그아웃. 서버가 무상태(JWT)이면 클라이언트 토큰 폐기로 충분하며, 서버 측 블랙리스트 운영 시 토큰을 무효화한다.

**2. Endpoint + Method**
`POST /auth/logout`

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
  "meta": { "path": "/auth/logout", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/auth/logout", "timestamp": 1733132400000 }
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
내 연주 이력을 페이지 단위(기본 3개)로 조회한다. 각 항목은 영역별 **문제 개수**(`state != GOOD`) 통계를 포함하며, 협주 기록은 합성 영상 ID를 함께 반환한다. (`feedback_events` 엔 GOOD도 저장되지만 stats는 문제만 센다 — DESIGN #25)

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
| items[].song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| items[].played_at | string(datetime) | Y | 연주 시각 | "2026-06-02T09:30:00+09:00" |
| items[].mode | string | Y | 모드(solo/duet) | "duet" |
| items[].stats.pitch | number | Y | 음정 문제 개수(GOOD 제외) | 3 |
| items[].stats.rhythm | number | Y | 박자 피드백 개수 | 1 |
| items[].stats.posture | number | Y | 자세 피드백 개수 | 2 |
| items[].duet_composite_id | number | N | 협주 합성 영상 ID(협주 기록만) | 5 |

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
      { "session_id": 12, "song_title": "반짝 반짝 작은별", "played_at": "2026-06-02T09:30:00+09:00",
        "mode": "duet", "stats": { "pitch": 3, "rhythm": 1, "posture": 2 }, "duet_composite_id": 5 },
      { "session_id": 10, "song_title": "반짝 반짝 작은별", "played_at": "2026-06-01T18:10:00+09:00",
        "mode": "solo", "stats": { "pitch": 0, "rhythm": 2, "posture": 1 } }
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

## 2.3 집중 반복 레슨 추천 조회

**1. API 설명**
세션 간 누적 폴백 3회 이상으로 추천된(`focus_recommended`) 약점 마디 목록을 조회한다.

**2. Endpoint + Method**
`GET /me/focus-lessons`

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
| lessons | array | Y | 추천 약점 마디 목록 | [] |
| lessons[].song_id | number | Y | 곡 ID | 1 |
| lessons[].song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| lessons[].measure_index | number | Y | 마디 번호 | 1 |
| lessons[].fallback_count | number | Y | 누적 폴백 횟수 | 3 |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "lessons": [
      { "song_id": 1, "song_title": "반짝 반짝 작은별", "measure_index": 1, "fallback_count": 3 },
      { "song_id": 1, "song_title": "반짝 반짝 작은별", "measure_index": 5, "fallback_count": 4 }
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
  "meta": { "path": "/me/focus-lessons", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/me/focus-lessons", "timestamp": 1733132400000 }
}
```

---

## 2.4 집중 반복 레슨 완료 보고

**1. API 설명**
한 약점 마디의 집중 반복 레슨(10회)을 마쳤음을 보고한다. `MeasureProgress.focus_completed`·`focus_attempts` 를 갱신한다. (집중 레슨은 별도 Session 없이 처리)

**2. Endpoint + Method**
`POST /me/focus-lessons/{song_id}/{measure_index}/complete`

**3. Path Parameter**
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| song_id | number | Y | 곡 ID | 1 |
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
| song_id | number | Y | 곡 ID | 1 |
| measure_index | number | Y | 마디 번호 | 1 |
| focus_completed | boolean | Y | 완료 여부 | true |
| focus_attempts | number | Y | 누적 완료 횟수 | 1 |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": { "song_id": 1, "measure_index": 1, "focus_completed": true, "focus_attempts": 1 }
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
  "meta": { "path": "/me/focus-lessons/1/1/complete", "timestamp": 1733132400000 }
}
```
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "추천된 집중 레슨이 아닙니다.",
  "code": "PRG_404_001",
  "meta": { "path": "/me/focus-lessons/1/99/complete", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/me/focus-lessons/1/1/complete", "timestamp": 1733132400000 }
}
```

---

## 2.5 협주 영상 목록 조회

**1. API 설명**
내가 참여한 협주의 좌우 분할 합성 영상 목록을 조회한다.

**2. Endpoint + Method**
`GET /me/duet-videos`

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
| videos | array | Y | 협주 영상 목록 | [] |
| videos[].duet_composite_id | number | Y | 합성 영상 ID | 5 |
| videos[].song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| videos[].partner_name | string | Y | 협주 상대 이름 | "이준호" |
| videos[].composite_video_url | string | N | 합성 영상 URL(ready 시) | "/media/duet/5.mp4" |
| videos[].status | string | Y | 합성 상태(pending/processing/ready/failed) | "ready" |
| videos[].created_at | string(datetime) | Y | 생성 시각 | "2026-06-02T09:35:00+09:00" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "videos": [
      { "duet_composite_id": 5, "song_title": "반짝 반짝 작은별", "partner_name": "이준호",
        "composite_video_url": "/media/duet/5.mp4", "status": "ready",
        "created_at": "2026-06-02T09:35:00+09:00" }
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
  "meta": { "path": "/me/duet-videos", "timestamp": 1733132400000 }
}
```
`500 Internal Server Error`
```json
{
  "success": false,
  "status": 500,
  "message": "서버 내부 오류가 발생했습니다.",
  "code": "COM_500_001",
  "meta": { "path": "/me/duet-videos", "timestamp": 1733132400000 }
}
```

---

## 2.6 협주 합성 영상 단건 조회

**1. API 설명**
협주 합성 영상 1건의 상태를 조회한다. `POST /sessions/{id}/complete` 가 돌려준 `duet_composite_id` 로 합성 잡 진행 상태(`processing → ready/failed`)를 폴링하는 용도다. (합성 잡 = DESIGN #38 `BackgroundTasks`+ffmpeg)

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
해당 곡으로 녹음이 있는 다른 연주자(협주 상대) 목록을 조회한다.

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
| partners | array | Y | 협주 상대 목록(없으면 빈 배열) | [] |
| partners[].recording_id | number | Y | 협주에 사용할 녹음 ID | 8 |
| partners[].user_name | string | Y | 연주자 이름 | "이준호" |
| partners[].song_title | string | Y | 곡명 | "반짝 반짝 작은별" |
| partners[].recorded_at | string(datetime) | Y | 녹음 시각 | "2026-05-30T12:00:00+09:00" |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "partners": [
      { "recording_id": 8, "user_name": "이준호", "song_title": "반짝 반짝 작은별", "recorded_at": "2026-05-30T12:00:00+09:00" }
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
연주 세션을 생성한다. `mode` 가 `duet` 이면 `partner_recording_id` 가 필요하다.

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

**9. Success Response Example (2xx)**
`201 Created`
```json
{
  "success": true,
  "status": 201,
  "message": "리소스가 생성되었습니다.",
  "data": { "session_id": 12, "status": "created" }
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

**6. Request Body** (client → server 메시지, 마디마다)
측정 입력을 보낸다. 오디오·프레임 바이트는 별도 바이너리 프레임으로 스트리밍하고, 아래 JSON 메시지로 마디 경계를 알린다(정확한 바이너리 프레이밍은 구현 시 확정). state는 백엔드가 측정해 만든다.

| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| type | string | Y | 메시지 타입 | "measure" |
| measure_index | number | Y | 현재 마디 | 12 |
| audio_ref | string | N | 직전 바이너리 오디오 청크 식별자 | "chunk-12" |
| frame_ref | string | N | 직전 바이너리 영상 프레임 식별자 | "frame-12" |

**7. Request Example (JSON)**
```json
{ "type": "measure", "measure_index": 12, "audio_ref": "chunk-12", "frame_ref": "frame-12" }
```

**8. Response Body** (server → client 메시지)
| Name | Type | Required | Description | Example |
|---|---|---|---|---|
| type | string | Y | 메시지 타입 | "feedback" |
| measure_index | number | Y | 현재 마디 | 12 |
| items | array | Y | 도메인별 피드백(reward 낮은 영역 먼저, 동률 자세 우선) | [] |
| items[].domain | string | Y | 영역(pitch/rhythm/posture) | "pitch" |
| items[].action_id | string | Y | 액션 ID. `-01`=POSITIVE(GOOD 격려) · `-02+`=교정 | "PT-03" |
| items[].action | string | Y | 액션명 | "PITCH_DOWN" |
| items[].feedback | string | Y | 피드백 문구 | "음정을 내리세요" |
| items[].delegated_from | string | N | 위임 출처 영역(슈퍼바이저가 다른 도메인으로 라우팅해 대신 교정 시) | "rhythm" |
| fallback | object | N | 슈퍼바이저 폴백(위임할 GOOD 아닌 동료가 없을 때만). 없으면 생략 | null |
| fallback.message | string | N | 폴백 고정 메시지 | "여기서 계속 같은 문제가..." |
| fallback.fallback_count | number | N | 해당 마디 누적 폴백 횟수(집중레슨 추천 기준) | 3 |

> GOOD 도메인은 `action_id=-01`(POSITIVE) item으로 실시간 격려를 보낸다(WS 전달 + `feedback_events` 에도 기록 — DESIGN #25).
> 폴백 마디에선 막힌 도메인은 item 없이 `fallback` 객체로 대신 표현하고, 나머지 GOOD 도메인은 POSITIVE item을 함께 보낸다.

**9. Success Response Example (2xx)**
`101 Switching Protocols` (WebSocket 연결 수립 후 메시지 교환)

교정 + 위임 라우팅 (음정 교정, 박자→자세 위임):
```json
{
  "type": "feedback",
  "measure_index": 12,
  "items": [
    { "domain": "pitch", "action_id": "PT-03", "action": "PITCH_DOWN", "feedback": "음정을 내리세요" },
    { "domain": "posture", "action_id": "PS-03", "action": "SHOULDER_BALANCE", "feedback": "양쪽 어깨 높이를 균형 있게 맞추세요.", "delegated_from": "rhythm" }
  ],
  "fallback": null
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
    { "domain": "posture", "action_id": "PS-01", "action": "POSITIVE_T", "feedback": "잘 하고 있습니다. 계속 유지하세요" }
  ],
  "fallback": null
}
```

폴백 (음정이 막혔으나 위임할 동료가 없음 — 나머지는 POSITIVE):
```json
{
  "type": "feedback",
  "measure_index": 15,
  "items": [
    { "domain": "rhythm", "action_id": "RH-01", "action": "POSITIVE_RHYTHM", "feedback": "잘 하고 있습니다. 계속 유지하세요" },
    { "domain": "posture", "action_id": "PS-01", "action": "POSITIVE_T", "feedback": "잘 하고 있습니다. 계속 유지하세요" }
  ],
  "fallback": { "message": "여기서 계속 같은 문제가 발생해요. 나중에 반복 연습하면서 개선해봐요", "fallback_count": 3 }
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
세션의 마디별 누적 마킹을 조회한다. 이번 세션(채움)과 같은 user×song 의 모드 무관 직전 완료 세션(외곽선)을 함께 반환한다. 마킹은 **문제 마디만**(`state != GOOD`) 표시한다 — `feedback_events` 엔 GOOD도 저장되지만 결과 화면은 문제 위주다(DESIGN #25).

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
| mode | string | Y | 모드 | "duet" |
| measures | array | Y | 마디별 마킹 | [] |
| measures[].measure_index | number | Y | 마디 번호 | 1 |
| measures[].current | array | Y | 이번 세션 마킹(채움) | [] |
| measures[].current[].domain | string | Y | 영역 | "pitch" |
| measures[].current[].feedback | string | Y | 피드백(도메인당 1개) | "음정을 내리세요" |
| measures[].previous | array | Y | 직전 세션 마킹(외곽선) | [] |

**9. Success Response Example (2xx)**
`200 OK`
```json
{
  "success": true,
  "status": 200,
  "message": "요청에 성공했습니다.",
  "data": {
    "session_id": 12, "song_id": 1, "mode": "duet",
    "measures": [
      { "measure_index": 1,
        "current": [ { "domain": "pitch", "feedback": "음정을 내리세요" } ],
        "previous": [ { "domain": "rhythm", "feedback": "박자보다 늦게 연주하고 있습니다" } ] }
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
결과 화면의 마디 상세 모달 데이터(큰 악보 + 이번/이전 세션 마킹)를 조회한다.

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
| notes | array | Y | 음표 배열 | [] |
| current_markings | array | Y | 이번 세션 마킹 | [] |
| current_markings[].domain | string | Y | 영역 | "pitch" |
| current_markings[].feedback | string | Y | 피드백(도메인당 1개) | "음정을 내리세요" |
| previous_markings | array | Y | 이전 세션 마킹(참고) | [] |

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
    "current_markings": [ { "domain": "pitch", "feedback": "음정을 내리세요" } ],
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
`404 Not Found`
```json
{
  "success": false,
  "status": 404,
  "message": "존재하지 않는 세션입니다.",
  "code": "SES_404_001",
  "meta": { "path": "/sessions/999/measures/1", "timestamp": 1733132400000 }
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
세션의 AI 상세 분석(디브리핑 + 영역별 수준·진단·연습)을 조회한다. 없으면 첫 호출에서 `/coach` LLM(OpenAI)으로 **동기 생성**(수 초 블로킹)한 뒤 캐시하며, 이후 같은 세션은 저장본을 반환한다. (백그라운드 잡 아님 — DESIGN #31)

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
    }
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
