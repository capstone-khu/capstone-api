"""fix seed session played_at to utc

Revision ID: 0009_fix_seed_played_at
Revises: 0008_analysis_reports
Create Date: 2026-06-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_fix_seed_played_at"
down_revision: str | None = "0008_analysis_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KST_PLAYED_AT = "2026-06-01 10:00:00"
_UTC_PLAYED_AT = "2026-06-01 01:00:00"
_PARTNER_NAME = "손수민"
_SONG_NUMBER = 1


def upgrade() -> None:
    _update_seed_session(_KST_PLAYED_AT, _UTC_PLAYED_AT)


def downgrade() -> None:
    _update_seed_session(_UTC_PLAYED_AT, _KST_PLAYED_AT)


def _update_seed_session(old: str, new: str) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE sessions SET started_at = :new, ended_at = :new "
            "WHERE user_id = (SELECT id FROM users WHERE name = :name) "
            "AND song_id = (SELECT id FROM songs WHERE number = :number) "
            "AND started_at = :old AND ended_at = :old"
        ),
        {"new": new, "old": old, "name": _PARTNER_NAME, "number": _SONG_NUMBER},
    )
