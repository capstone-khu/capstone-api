"""create song, song_measure, session, recording

Revision ID: 0003_song_session_recording
Revises: 0002_seed_demo_users
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_song_session_recording"
down_revision: str | None = "0002_seed_demo_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "songs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("bpm", sa.Integer(), nullable=False),
        sa.Column("time_signature", sa.String(length=10), nullable=False),
        sa.Column("total_measures", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "song_measures",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("measure_index", sa.Integer(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
        sa.UniqueConstraint("song_id", "measure_index"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.Enum("solo", "duet", name="session_mode"), nullable=False),
        sa.Column("partner_recording_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "created",
                "in_progress",
                "completed",
                "aborted",
                name="session_status",
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
    )

    op.create_table(
        "recordings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("audio_url", sa.String(length=500), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=False),
        sa.Column(
            "available_for_duet",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"]),
    )

    op.create_foreign_key(
        "fk_sessions_partner_recording_id",
        "sessions",
        "recordings",
        ["partner_recording_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sessions_partner_recording_id", "sessions", type_="foreignkey"
    )
    op.drop_table("recordings")
    op.drop_table("sessions")
    op.drop_table("song_measures")
    op.drop_table("songs")
