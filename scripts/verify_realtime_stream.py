"""실시간 라이브 루프(WS) + 슈퍼바이저가 제대로 도는지 확인하는 스크립트.

연주를 흉내 내 마디마다 오디오·프레임을 보내고, 마디별 피드백과 위임(−00) 보강,
종료 후 적재를 점검한다.

- 준비: 위임을 유발하려 박자 Q(LATE/RHYTHM_CATCH_UP)를 음수로 시드 →
        자연 교정 대신 CALL_SUPERVISOR(−00)가 argmax 로 떠오른다. 토큰·세션 생성.
- 스트림: 픽스처를 마디 단위로 보내고 feedback 수신. −00 마디는 cause.pending=true 로
          먼저 오고, 비동기 슈퍼바이저가 feedback_update 로 교체.
- 적재: /complete 후 feedback_events·위임 행 cause_domain 확인.

오디오는 reference.mp3 를 PCM16 으로(서버는 디코드 없이 받음),
영상은 performance.mp4 프레임을 JPEG 로 보낸다.

먼저 서버를 띄운 뒤 실행한다:
  uv run --group audio --group vision uvicorn app.main:app --port 8011 &
  uv run --group audio --group vision python scripts/verify_realtime_stream.py
"""

import asyncio
import json
import sys
import time
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


async def _seed_negative_q() -> None:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO q_table_entries "
                "(user_id, domain, state, action, q_value, update_count) "
                "VALUES (:u, 'rhythm', 'LATE', 'RHYTHM_CATCH_UP', -5.0, 5) "
                "ON DUPLICATE KEY UPDATE q_value = -5.0, update_count = 5"
            ),
            {"u": USER_ID},
        )
        await s.commit()


async def _clear_seed() -> None:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        await s.execute(
            text(
                "DELETE FROM q_table_entries WHERE user_id = :u AND domain = 'rhythm' "
                "AND state = 'LATE' AND action = 'RHYTHM_CATCH_UP'"
            ),
            {"u": USER_ID},
        )
        await s.commit()


async def _wait_until(predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.1)
    return predicate()


async def _prepare(client) -> tuple[str, int]:
    from app.domain.auth.security import create_access_token

    token = create_access_token(USER_ID)
    resp = await client.post(
        f"{BASE}/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"song_id": SONG_ID, "mode": "solo"},
    )
    session_id = resp.json()["data"]["session_id"]
    print(f"  세션 생성: session_id={session_id} (status {resp.status_code})")
    return token, session_id


async def _stream(client, token: str, session_id: int):
    import websockets

    from app.domain.agent.score import load_timed_score

    windows = load_timed_score(SONG_ID).measure_windows()
    audio = _audio_chunks()
    video = _video_frames(windows[-1][2])

    feedbacks: dict[int, list[dict]] = {}
    updates: list[dict] = []
    url = f"{WS_BASE}/sessions/{session_id}/stream?token={token}"
    async with websockets.connect(url, max_size=None) as ws:

        async def collect():
            try:
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("type") == "feedback":
                        feedbacks[msg["measure_index"]] = msg["items"]
                    elif msg.get("type") == "feedback_update":
                        updates.append(msg)
            except Exception:
                pass

        collector = asyncio.create_task(collect())
        ai = vi = 0
        for measure, _start, end in windows:
            while ai < len(audio) and audio[ai][0] / 1000.0 < end:
                await ws.send(_frame(KIND_AUDIO, *audio[ai]))
                ai += 1
            while vi < len(video) and video[vi][0] / 1000.0 < end:
                await ws.send(_frame(KIND_VIDEO, *video[vi]))
                vi += 1
            await ws.send(json.dumps({"type": "measure", "measure_index": measure}))

        await _wait_until(lambda: len(feedbacks) >= len(windows), 30)
        delegated = [
            (mi, it)
            for mi, items in feedbacks.items()
            for it in items
            if it["action_id"].endswith("-00")
        ]
        await _wait_until(lambda: len(updates) >= len(delegated), 30)
        complete_ok = await _complete(client, token, session_id)
        collector.cancel()

    stream_ok = len(feedbacks) >= len(windows)
    for items in feedbacks.values():
        stream_ok &= bool(items) and all(it["action_id"] in NORMAL_IDS for it in items)

    print(f"  마디 {len(feedbacks)}개, 위임(-00) {len(delegated)}건, "
          f"feedback_update {len(updates)}건")
    resolved = {(u["measure_index"], u["item"]["domain"]) for u in updates}
    sup_ok = len(delegated) >= 1 and len(updates) >= len(delegated)
    for mi, it in delegated:
        sup_ok &= it.get("cause", {}).get("pending") is True
        sup_ok &= (mi, it["domain"]) in resolved
    for u in updates[:3]:
        item = u["item"]
        print(f"    update m{u['measure_index']} {item['domain']}→"
              f"cause={item['cause'].get('domain')}: {item['feedback'][:34]}")
    print(f"  스트림 {'OK' if stream_ok else 'FAIL'} / "
          f"슈퍼바이저 {'OK' if sup_ok else 'FAIL'}")
    return stream_ok, sup_ok, complete_ok, feedbacks, delegated


async def _complete(client, token: str, session_id: int) -> bool:
    from app.common.media import media_path

    with open(VIDEO, "rb") as vf, open(AUDIO, "rb") as af:
        files = {
            "audio": ("rec.mp3", af, "audio/mpeg"),
            "video": ("rec.mp4", vf, "video/mp4"),
        }
        resp = await client.post(
            f"{BASE}/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
    data = resp.json().get("data", {})
    rid = data.get("recording_id")
    file_ok = rid is not None and media_path(f"/media/recordings/{rid}.mp4").exists()
    ok = resp.status_code == 200 and data.get("session_id") == session_id and file_ok
    print(f"  /complete: status {resp.status_code} recording_id={rid} "
          f"file={'OK' if file_ok else 'X'}  {'OK' if ok else 'FAIL'}")
    return ok


async def _check_db(session_id: int, feedbacks: dict, delegated: list) -> bool:
    from sqlalchemy import text

    from app.common.persistence import AsyncSessionLocal

    expected = sum(len(items) for items in feedbacks.values())
    async with AsyncSessionLocal() as s:
        count = (
            await s.execute(
                text("SELECT COUNT(*) FROM feedback_events WHERE session_id = :s"),
                {"s": session_id},
            )
        ).scalar()
        sup_rows = (
            await s.execute(
                text(
                    "SELECT measure_index, domain, cause_domain, feedback "
                    "FROM feedback_events WHERE session_id = :s "
                    "AND action = 'CALL_SUPERVISOR' ORDER BY measure_index"
                ),
                {"s": session_id},
            )
        ).all()

    rows_ok = count == expected and count > 0
    resolved = [r for r in sup_rows if r[2] is not None]
    cause_ok = (
        len(sup_rows) == len(delegated)
        and len(resolved) == len(sup_rows)
        and len(sup_rows) > 0
    )
    print(f"  feedback_events: {count}행 (송신 {expected})  "
          f"{'OK' if rows_ok else 'FAIL'}")
    print(f"  위임 행 {len(sup_rows)}개 · cause_domain 채워짐 {len(resolved)}개  "
          f"{'OK' if cause_ok else 'FAIL'}")
    for r in sup_rows[:3]:
        print(f"    m{r[0]} {r[1]}→{r[2]}: {r[3][:34]}")
    return rows_ok and cause_ok


async def main() -> int:
    import httpx

    results: dict[str, bool] = {}
    await _seed_negative_q()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("\n[준비]")
            token, session_id = await _prepare(client)

            print("\n[스트림]")
            (
                results["stream"],
                results["supervisor"],
                results["complete"],
                feedbacks,
                delegated,
            ) = await _stream(client, token, session_id)

            print("\n[적재]")
            results["persistence"] = await _check_db(session_id, feedbacks, delegated)
    finally:
        await _clear_seed()

    print("\n=== 요약 ===")
    failed = False
    for name, res in results.items():
        failed |= not res
        print(f"  {name:12} {'PASS' if res else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
