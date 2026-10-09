"""create users and identities tables

Revision ID: 0002_users
Revises: 0001_notes
Create Date: 2026-10-09 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_users"
down_revision: str | None = "0001_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "identities",
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("provider", "subject"),
    )
    op.create_index("ix_identities_user", "identities", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_identities_user", table_name="identities")
    op.drop_table("identities")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
