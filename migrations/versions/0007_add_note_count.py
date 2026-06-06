"""add note_count to song_measures notes

Revision ID: 0007_add_note_count
Revises: 0006_duet_videos
Create Date: 2026-06-06

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_add_note_count"
down_revision: str | None = "0006_duet_videos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOTE_COUNTS = {
    1: [1, 1, 1, 1],
    2: [1, 1, 2],
    3: [1, 1, 1, 1],
    4: [1, 1, 2],
    5: [1, 1, 1, 1],
    6: [1, 1, 2],
    7: [1, 1, 1, 1],
    8: [1, 1, 2],
    9: [1, 1, 1, 1],
    10: [1, 1, 2],
    11: [1, 1, 1, 1],
    12: [1, 1, 2],
}


def upgrade() -> None:
    bind = op.get_bind()
    song_id = bind.execute(
        sa.text("SELECT id FROM songs WHERE number = 1")
    ).scalar_one()

    rows = bind.execute(
        sa.text(
            "SELECT measure_index, notes FROM song_measures "
            "WHERE song_id = :song_id ORDER BY measure_index"
        ),
        {"song_id": song_id},
    ).all()

    for measure_index, notes_json in rows:
        notes = json.loads(notes_json)
        counts = _NOTE_COUNTS[measure_index]
        for i, note in enumerate(notes):
            note["note_count"] = counts[i]
        bind.execute(
            sa.text(
                "UPDATE song_measures SET notes = :notes "
                "WHERE song_id = :song_id AND measure_index = :measure_index"
            ),
            {
                "notes": json.dumps(notes, ensure_ascii=False),
                "song_id": song_id,
                "measure_index": measure_index,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    song_id = bind.execute(
        sa.text("SELECT id FROM songs WHERE number = 1")
    ).scalar_one()

    rows = bind.execute(
        sa.text(
            "SELECT measure_index, notes FROM song_measures "
            "WHERE song_id = :song_id ORDER BY measure_index"
        ),
        {"song_id": song_id},
    ).all()

    for measure_index, notes_json in rows:
        notes = json.loads(notes_json)
        for note in notes:
            note.pop("note_count", None)
        bind.execute(
            sa.text(
                "UPDATE song_measures SET notes = :notes "
                "WHERE song_id = :song_id AND measure_index = :measure_index"
            ),
            {
                "notes": json.dumps(notes, ensure_ascii=False),
                "song_id": song_id,
                "measure_index": measure_index,
            },
        )
