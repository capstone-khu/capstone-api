"""협주(duet) 세션 종료·합성·조회가 잘 동작하는 지 확인하는 스크립트.

duet 세션을 만들어 multipart 로 /complete 하면 협주 합성 잡이 백그라운드로 돌고,
GET /duet-videos/{id} 로 상태를 폴링해 합성 결과를 확인한다(previous-markings 도 점검).

- 종료: duet 세션 생성(partner_recording_id=1) → multipart /complete → id 얻음.
- 합성: GET /duet-videos/{id} 를 pending→processing→ready/failed 까지 폴링.
        ffmpeg 가 있으면 ready + /media/duet/{id}.mp4 생성, 없으면 failed(로컬 한정).
- 마킹: 같은 세션의 previous-markings 가 직전 완료 세션 마킹을 반환.

먼저 서버를 띄운 뒤 실행한다:
  uv run uvicorn app.main:app --port 8011 &
  uv run python scripts/verify_duet_complete.py
"""

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8011"
AUDIO = "fixtures/media/twinkle_twinkle.violin_reference.mp3"
VIDEO = "fixtures/media/twinkle_twinkle.violin_performance.mp4"
SONG_ID = 1
USER_ID = 1
PARTNER_RECORDING_ID = 1


async def _create_session(client, token: str) -> int:
    resp = await client.post(
        f"{BASE}/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "song_id": SONG_ID,
            "mode": "duet",
            "partner_recording_id": PARTNER_RECORDING_ID,
        },
    )
    data = resp.json()["data"]
    print(f"  duet 세션 생성: session_id={data['session_id']} "
          f"partner={data.get('partner_name')} (status {resp.status_code})")
    return data["session_id"]


async def _complete(client, token: str, session_id: int) -> int | None:
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
    duet_id = data.get("duet_composite_id")
    print(f"  /complete: status {resp.status_code} "
          f"recording_id={data.get('recording_id')} duet_composite_id={duet_id}")
    return duet_id


async def _poll(client, token: str, duet_id: int) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(60):
        resp = await client.get(f"{BASE}/duet-videos/{duet_id}", headers=headers)
        data = resp.json().get("data", {})
        if data.get("status") in ("ready", "failed"):
            return data
        await asyncio.sleep(1)
    return data


async def main() -> int:
    import httpx

    from app.common.media import media_path
    from app.domain.auth.security import create_access_token

    results: dict[str, bool] = {}
    token = create_access_token(USER_ID)
    has_ffmpeg = shutil.which("ffmpeg") is not None

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n[종료]")
        session_id = await _create_session(client, token)
        duet_id = await _complete(client, token, session_id)
        results["complete"] = duet_id is not None

        print("\n[합성]")
        final = await _poll(client, token, duet_id) if duet_id else {}
        status = final.get("status")
        flow_ok = bool(final.get("song_title")) and bool(final.get("partner_name"))
        print(f"  최종 status={status}, song={final.get('song_title')}, "
              f"partner={final.get('partner_name')}")
        print(f"  url={final.get('composite_video_url')}")
        if has_ffmpeg:
            file_ok = status == "ready" and media_path(
                final.get("composite_video_url", "/media/duet/x")
            ).exists()
            results["synthesis"] = flow_ok and file_ok
            print(f"  ffmpeg 있음 → ready+파일 {'OK' if file_ok else 'FAIL'}")
        else:
            results["synthesis"] = flow_ok and status in ("ready", "failed")
            print("  [note] 로컬 ffmpeg 없음 → 합성은 prod 에서 검증. 흐름만 확인")

        print("\n[마킹]")
        resp = await client.get(
            f"{BASE}/sessions/{session_id}/previous-markings",
            headers={"Authorization": f"Bearer {token}"},
        )
        pm = resp.json().get("data", {})
        results["previous_markings"] = resp.status_code == 200 and "measures" in pm
        print(f"  previous-markings: status {resp.status_code}, "
              f"previous_session_id={pm.get('previous_session_id')}, "
              f"measures={len(pm.get('measures', []))}")

    print("\n=== 요약 ===")
    failed = False
    for name, res in results.items():
        failed |= not res
        print(f"  {name:18} {'PASS' if res else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
