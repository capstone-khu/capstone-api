"""실시간 라이브 루프(WS)가 제대로 도는지 확인하는 스크립트.

연주를 흉내 내 마디마다 마이크 오디오·카메라 프레임을 WebSocket 으로 보내고,
서버가 돌려주는 마디별 피드백과 종료 후 적재 상태를 세 단계로 점검한다.

- 준비: 토큰 발급 → 세션 생성(REST).
- 스트림: 픽스처를 마디 윈도우 단위로 흘려보내고 feedback(도메인별 item) 수신·검증.
- 적재: /complete 후 feedback_events·q_table_entries 확인.

오디오는 reference.mp3 를 PCM16 으로 풀어 보내고(서버는 디코드 없이 받음),
영상은 performance.mp4 프레임을 JPEG 로 인코드해 보낸다(둘은 다른 녹음이라
음악적 정확도가 아니라 파이프라인 동작 확인용이다).

먼저 서버를 띄운 뒤 실행한다:
  uv run --group audio --group vision uvicorn app.main:app --port 8011 &
  uv run --group audio --group vision python scripts/verify_realtime_stream.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8011"
WS_BASE = "ws://127.0.0.1:8011"
AUDIO = "fixtures/media/twinkle_twinkle.violin_reference.mp3"
VIDEO = "fixtures/media/twinkle_twinkle.violin_performance.mp4"
SONG_ID = 1
USER_ID = 1
SAMPLE_RATE = 48000
CHUNK_MS = 100
KIND_AUDIO = 0x01
KIND_VIDEO = 0x02
NORMAL_IDS = {
    "PT-00", "PT-01", "PT-02", "PT-03",
    "RH-00", "RH-01", "RH-02", "RH-03", "RH-04", "RH-05",
    "PS-00", "PS-01", "PS-02", "PS-03", "PS-04", "PS-05",
    "PS-06", "PS-07", "PS-99",
}


def _frame(kind: int, ts_ms: int, payload: bytes) -> bytes:
    return bytes([kind]) + int(ts_ms).to_bytes(4, "big") + payload


def _audio_chunks() -> list[tuple[int, bytes]]:
    import librosa
    import numpy as np

    y, _ = librosa.load(AUDIO, sr=SAMPLE_RATE, mono=True)
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    step = SAMPLE_RATE * CHUNK_MS // 1000
    chunks = []
    for i in range(0, len(y), step):
        ts = i * 1000 // SAMPLE_RATE
        payload = pcm[i * 2 : (i + step) * 2]
        if payload:
            chunks.append((ts, payload))
    return chunks


def _video_frames(end_s: float) -> list[tuple[int, bytes]]:
    import cv2

    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ts = int(idx / fps * 1000)
        idx += 1
        if ts / 1000.0 >= end_s:
            break
        ok2, buf = cv2.imencode(".jpg", frame)
        if ok2:
            frames.append((ts, buf.tobytes()))
    cap.release()
    return frames


async def _prepare(client) -> tuple[str, int]:
    from app.domain.auth.security import create_access_token

    token = create_access_token(USER_ID)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        f"{BASE}/sessions",
        headers=headers,
        json={"song_id": SONG_ID, "mode": "solo"},
    )
    session_id = resp.json()["data"]["session_id"]
    print(f"  세션 생성: session_id={session_id} (status {resp.status_code})")
    return token, session_id


async def _stream(
    client, token: str, session_id: int
) -> tuple[bool, bool, list[dict]]:
    import websockets

    from app.domain.agent.score import load_timed_score

    windows = load_timed_score(SONG_ID).measure_windows()
    audio = _audio_chunks()
    video = _video_frames(windows[-1][2])

    received: list[dict] = []
    ok = True
    url = f"{WS_BASE}/sessions/{session_id}/stream?token={token}"
    async with websockets.connect(url, max_size=None) as ws:
        ai = vi = 0
        for measure, _start, end in windows:
            while ai < len(audio) and audio[ai][0] / 1000.0 < end:
                await ws.send(_frame(KIND_AUDIO, audio[ai][0], audio[ai][1]))
                ai += 1
            while vi < len(video) and video[vi][0] / 1000.0 < end:
                await ws.send(_frame(KIND_VIDEO, video[vi][0], video[vi][1]))
                vi += 1
            await ws.send(json.dumps({"type": "measure", "measure_index": measure}))
            msg = json.loads(await ws.recv())
            received.append(msg)

            items = msg.get("items", [])
            domains = {it["domain"] for it in items}
            ids_ok = all(it["action_id"] in NORMAL_IDS for it in items)
            good_ok = all(
                it["action_id"].endswith("-01")
                for it in items
                if it["action"].startswith("POSITIVE")
            )
            mark = "OK" if (items and ids_ok and good_ok) else "FAIL"
            ok &= bool(items) and ids_ok and good_ok
            summary = ", ".join(f"{it['domain']}:{it['action_id']}" for it in items)
            print(f"  m{measure:<2} {sorted(domains)} {summary}  {mark}")

        # 정상 종료는 WS close 전에 /complete 를 먼저 호출(계약 §4.2)
        print("\n[적재]")
        complete_ok = await _complete(client, token, session_id)
    return ok, complete_ok, received


async def _complete(client, token: str, session_id: int) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(f"{BASE}/sessions/{session_id}/complete", headers=headers)
    ok = resp.status_code == 200 and resp.json()["data"]["session_id"] == session_id
    print(f"  /complete: status {resp.status_code}  {'OK' if ok else 'FAIL'}")
    return ok


async def _check_db(session_id: int, received: list[dict]) -> bool:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal

    expected = sum(len(m.get("items", [])) for m in received)
    async with AsyncSessionLocal() as s:
        count = (
            await s.execute(
                text(
                    "SELECT COUNT(*) FROM feedback_events WHERE session_id = :s"
                ),
                {"s": session_id},
            )
        ).scalar()
        by_domain = (
            await s.execute(
                text(
                    "SELECT domain, COUNT(*) FROM feedback_events "
                    "WHERE session_id = :s GROUP BY domain"
                ),
                {"s": session_id},
            )
        ).all()
        q_rows = (
            await s.execute(
                text(
                    "SELECT domain, COUNT(*) FROM q_table_entries "
                    "WHERE user_id = :u GROUP BY domain"
                ),
                {"u": USER_ID},
            )
        ).all()

    ok = count == expected and count > 0
    mark = "OK" if ok else "FAIL"
    print(f"  feedback_events: {count}행 (송신 item {expected})  {mark}")
    print(f"  도메인별: {dict(by_domain)}")
    print(f"  q_table_entries(user {USER_ID}): {dict(q_rows)}")
    return ok


async def main() -> int:
    import httpx

    results: dict[str, bool] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n[준비]")
        token, session_id = await _prepare(client)

        print("\n[스트림]")
        results["stream"], results["complete"], received = await _stream(
            client, token, session_id
        )
        results["persistence"] = await _check_db(session_id, received)

    print("\n=== 요약 ===")
    failed = False
    for name, res in results.items():
        failed |= not res
        print(f"  {name:12} {'PASS' if res else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
