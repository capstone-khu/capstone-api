"""seed songs

Revision ID: 0004_seed_songs
Revises: 0003_song_session_recording
Create Date: 2026-06-04

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_seed_songs"
down_revision: str | None = "0003_song_session_recording"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SONG = {
    "number": 1,
    "title": "반짝 반짝 작은별",
    "bpm": 96,
    "time_signature": "4/4",
    "total_measures": 12,
}

_MEASURES = [
    {"measure_index": 1, "notes": [
        {"pitch": "D4", "duration": "quarter", "position": 0, "lyric": "반", "note_count": 1},
        {"pitch": "D4", "duration": "quarter", "position": 1, "lyric": "짝", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 2, "lyric": "반", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 3, "lyric": "짝", "note_count": 1},
    ]},
    {"measure_index": 2, "notes": [
        {"pitch": "B4", "duration": "quarter", "position": 0, "lyric": "작", "note_count": 1},
        {"pitch": "B4", "duration": "quarter", "position": 1, "lyric": "은", "note_count": 1},
        {"pitch": "A4", "duration": "half", "position": 2, "lyric": "별", "note_count": 2},
    ]},
    {"measure_index": 3, "notes": [
        {"pitch": "G4", "duration": "quarter", "position": 0, "lyric": "아", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 1, "lyric": "름", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 2, "lyric": "답", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 3, "lyric": "게", "note_count": 1},
    ]},
    {"measure_index": 4, "notes": [
        {"pitch": "E4", "duration": "quarter", "position": 0, "lyric": "비", "note_count": 1},
        {"pitch": "E4", "duration": "quarter", "position": 1, "lyric": "치", "note_count": 1},
        {"pitch": "D4", "duration": "half", "position": 2, "lyric": "네", "note_count": 2},
    ]},
    {"measure_index": 5, "notes": [
        {"pitch": "A4", "duration": "quarter", "position": 0, "lyric": "동", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 1, "lyric": "쪽", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 2, "lyric": "하", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 3, "lyric": "늘", "note_count": 1},
    ]},
    {"measure_index": 6, "notes": [
        {"pitch": "F#4", "duration": "quarter", "position": 0, "lyric": "에", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 1, "lyric": "서", "note_count": 1},
        {"pitch": "E4", "duration": "half", "position": 2, "lyric": "도", "note_count": 2},
    ]},
    {"measure_index": 7, "notes": [
        {"pitch": "A4", "duration": "quarter", "position": 0, "lyric": "서", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 1, "lyric": "쪽", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 2, "lyric": "하", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 3, "lyric": "늘", "note_count": 1},
    ]},
    {"measure_index": 8, "notes": [
        {"pitch": "F#4", "duration": "quarter", "position": 0, "lyric": "에", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 1, "lyric": "서", "note_count": 1},
        {"pitch": "E4", "duration": "half", "position": 2, "lyric": "도", "note_count": 2},
    ]},
    {"measure_index": 9, "notes": [
        {"pitch": "D4", "duration": "quarter", "position": 0, "lyric": "반", "note_count": 1},
        {"pitch": "D4", "duration": "quarter", "position": 1, "lyric": "짝", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 2, "lyric": "반", "note_count": 1},
        {"pitch": "A4", "duration": "quarter", "position": 3, "lyric": "짝", "note_count": 1},
    ]},
    {"measure_index": 10, "notes": [
        {"pitch": "B4", "duration": "quarter", "position": 0, "lyric": "작", "note_count": 1},
        {"pitch": "B4", "duration": "quarter", "position": 1, "lyric": "은", "note_count": 1},
        {"pitch": "A4", "duration": "half", "position": 2, "lyric": "별", "note_count": 2},
    ]},
    {"measure_index": 11, "notes": [
        {"pitch": "G4", "duration": "quarter", "position": 0, "lyric": "아", "note_count": 1},
        {"pitch": "G4", "duration": "quarter", "position": 1, "lyric": "름", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 2, "lyric": "답", "note_count": 1},
        {"pitch": "F#4", "duration": "quarter", "position": 3, "lyric": "게", "note_count": 1},
    ]},
    {"measure_index": 12, "notes": [
        {"pitch": "E4", "duration": "quarter", "position": 0, "lyric": "비", "note_count": 1},
        {"pitch": "E4", "duration": "quarter", "position": 1, "lyric": "치", "note_count": 1},
        {"pitch": "D4", "duration": "half", "position": 2, "lyric": "네", "note_count": 2},
    ]},
]

_PARTNER_NAME = "손수민"
_PLAYED_AT = "2026-06-01 10:00:00"


def upgrade() -> None:
    bind = op.get_bind()

    song_id = bind.execute(
        sa.text(
            "INSERT INTO songs (number, title, bpm, time_signature, total_measures) "
            "VALUES (:number, :title, :bpm, :time_signature, :total_measures)"
        ),
        _SONG,
    ).lastrowid

    for measure in _MEASURES:
        bind.execute(
            sa.text(
                "INSERT INTO song_measures (song_id, measure_index, notes) "
                "VALUES (:song_id, :measure_index, :notes)"
            ),
            {
                "song_id": song_id,
                "measure_index": measure["measure_index"],
                "notes": json.dumps(measure["notes"], ensure_ascii=False),
            },
        )

    user_id = bind.execute(
        sa.text("SELECT id FROM users WHERE name = :name"),
        {"name": _PARTNER_NAME},
    ).scalar_one()

    session_id = bind.execute(
        sa.text(
            "INSERT INTO sessions "
            "(user_id, song_id, mode, status, started_at, ended_at) "
            "VALUES (:user_id, :song_id, 'solo', 'completed', :at, :at)"
        ),
        {"user_id": user_id, "song_id": song_id, "at": _PLAYED_AT},
    ).lastrowid

    recording_id = bind.execute(
        sa.text(
            "INSERT INTO recordings "
            "(session_id, user_id, song_id, audio_url, video_url, available_for_duet) "
            "VALUES (:session_id, :user_id, :song_id, '', '', 1)"
        ),
        {"session_id": session_id, "user_id": user_id, "song_id": song_id},
    ).lastrowid

    media_url = f"/media/recordings/{recording_id}.mp4"
    bind.execute(
        sa.text(
            "UPDATE recordings SET audio_url = :url, video_url = :url WHERE id = :id"
        ),
        {"url": media_url, "id": recording_id},
    )


def downgrade() -> None:
    bind = op.get_bind()
    song_ids = "(SELECT id FROM songs WHERE number = :number)"
    params = {"number": _SONG["number"]}
    bind.execute(
        sa.text(f"DELETE FROM recordings WHERE song_id IN {song_ids}"), params
    )
    bind.execute(
        sa.text(f"DELETE FROM sessions WHERE song_id IN {song_ids}"), params
    )
    bind.execute(
        sa.text(f"DELETE FROM song_measures WHERE song_id IN {song_ids}"), params
    )
    bind.execute(
        sa.text("DELETE FROM songs WHERE number = :number"), params
    )
