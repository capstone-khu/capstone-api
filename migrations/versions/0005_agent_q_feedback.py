"""create q_table_entries, feedback_events

Revision ID: 0005_agent_q_feedback
Revises: 0004_seed_songs
Create Date: 2026-06-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_agent_q_feedback"
down_revision: str | None = "0004_seed_songs"
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
        "q_table_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum("pitch", "rhythm", "posture", name="agent_domain"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("q_value", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "update_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "domain", "state", "action"),
    )

    op.create_table(
        "feedback_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("measure_index", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum("pitch", "rhythm", "posture", name="agent_domain"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("action_id", sa.String(length=10), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("q", sa.Float(), nullable=False),
        sa.Column("cause_domain", sa.String(length=10), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
    )
    op.create_index(
        "ix_feedback_events_session_measure",
        "feedback_events",
        ["session_id", "measure_index"],
    )


def downgrade() -> None:
    op.drop_table("feedback_events")
    op.drop_table("q_table_entries")
