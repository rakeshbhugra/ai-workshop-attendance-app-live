"""create notes table

Revision ID: 0001_notes
Revises:
Create Date: 2026-01-01 00:00:00+00:00

The example migration. Generate the next one with `make migration m="add x"`,
then *read the file it wrote* before committing — autogenerate is a good first
draft, not a finished migration. It routinely misses renames (it sees a drop plus
an add, which loses the data) and it never writes a data backfill for you.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_notes"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Covers the list endpoint's default query: "not archived, newest first".
    # It must match the Index declared in adapters/orm/tables.py exactly, or
    # `alembic check` reports drift and the next autogenerate writes a migration
    # to drop it.
    op.create_index("ix_notes_active_created_at", "notes", ["archived_at", "created_at"])


def downgrade() -> None:
    # Always write the downgrade. You will need it during a bad deploy, at which
    # point it is far too late to work out what it should have said.
    op.drop_index("ix_notes_active_created_at", table_name="notes")
    op.drop_table("notes")
