"""Imperative (classical) table definitions.

This is the load-bearing trick that keeps the domain pure: the domain entity
never inherits from a declarative Base and never imports SQLAlchemy. Instead this
module imports the entity and maps a table *onto* it. Persistence ignorance,
kept honest by the dependency check in ``scripts/check_dependency_rule.py``.

The cost is that you write the columns out by hand instead of getting them from
annotations. That is the whole cost, and it buys a domain you can unit-test with
no database and no import of SQLAlchemy anywhere near it.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text, Uuid

from attendance.adapters.orm.registry import metadata

note_table = Table(
    "notes",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("body", Text, nullable=False, default=""),
    # timezone=True so Postgres stores timestamptz. Naive timestamps are the
    # classic "works locally, wrong in prod" bug once a second region appears.
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    # Covers the list endpoint's default query: "not archived, newest first".
    # Without it that is a sequential scan on every page load once the table is
    # real. Index the query you actually run, not the column that looks
    # important. No DESC: a btree scans backwards just as fast, and the
    # direction only matters for mixed-direction ordering, which this has none of.
    Index("ix_notes_active_created_at", "archived_at", "created_at"),
)

user_table = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("email", String(320), nullable=False),
    Column("name", String(200), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # Not unique: two providers can report the same unverified address.
    Index("ix_users_email", "email"),
)

identity_table = Table(
    "identities",
    metadata,
    Column("provider", String(40), primary_key=True),
    Column("subject", String(200), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_identities_user", "user_id"),
)

# Every index and constraint must be declared *here*, not only in a migration.
# Alembic compares the database against this metadata, so an index that exists
# only in a migration file shows up as "removed" and the next autogenerate
# helpfully writes a migration to drop it. `alembic check` catches that drift —
# it runs against the models, so keep the two in step.
