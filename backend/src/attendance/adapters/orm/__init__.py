"""ORM wiring: call ``start_mappers()`` once before any session is used.

Mapping is a global, process-wide side effect, so it is explicit and idempotent
rather than an import-time surprise: a script that only wants ``metadata`` (say,
Alembic) can import this module without mutating the domain classes.
"""

from __future__ import annotations

from attendance.adapters.orm import attendance_tables  # noqa: F401 - register metadata
from attendance.adapters.orm.registry import mapper_registry, metadata
from attendance.adapters.orm.tables import identity_table, note_table, user_table
from attendance.domain.note import Note
from attendance.domain.user import Identity, User

__all__ = ["identity_table", "metadata", "note_table", "start_mappers", "user_table"]

_mappers_started = False


def start_mappers() -> None:
    """Attach the domain classes to their tables. Safe to call repeatedly — the
    test suite creates several apps in one process and would otherwise blow up on
    the second mapping attempt."""
    global _mappers_started
    if _mappers_started:
        return
    mapper_registry.map_imperatively(Note, note_table)
    mapper_registry.map_imperatively(User, user_table)
    mapper_registry.map_imperatively(Identity, identity_table)
    _mappers_started = True
