"""seed demo users

Revision ID: 0002_seed_demo_users
Revises: 0001_create_users
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_demo_users"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEMO_USERS = [
    ("신진수", "$argon2id$v=19$m=65536,t=3,p=4$g0cPG4xJz1qUphu6X+9zTw$We+yYvTqSH7WCqCUhMma5ldTpswcKts92ZhqSfkM5OY"),  # noqa: E501
    ("손수민", "$argon2id$v=19$m=65536,t=3,p=4$3CMqbFJAxC0WMniXmdSj3w$D9e3c230QiJQ0WsyZ8oadyOWQYOc+FFQ8ORwv6Kov9c"),  # noqa: E501
    ("이수련", "$argon2id$v=19$m=65536,t=3,p=4$xsagmPtISMt2M23iXGAKAg$JZZaH0zJSUcZ71RzQzt1ixTg/uJ3kPP9vOiQ8/WIV7c"),  # noqa: E501
    ("최진영", "$argon2id$v=19$m=65536,t=3,p=4$ZEAW44X6C5KDSiuHeMmLZg$6TNBX2wgCGL5k5//UYxLSLau5gqxcMuxjZjFp8TmfPw"),  # noqa: E501
]

_users = sa.table(
    "users",
    sa.column("name", sa.String),
    sa.column("password_hash", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        _users,
        [{"name": name, "password_hash": pw} for name, pw in _DEMO_USERS],
    )


def downgrade() -> None:
    names = [name for name, _ in _DEMO_USERS]
    op.execute(_users.delete().where(_users.c.name.in_(names)))
