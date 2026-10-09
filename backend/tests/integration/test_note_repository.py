"""Integration tests — the real SQLAlchemy adapter against a real database.

This tier exists to answer one question the service tests cannot: **does the fake
lie?** Everything below is deliberately a mirror of an assertion made against
``FakeNoteRepository``, run again through actual SQL. When the two disagree, the
service suite has been green for the wrong reason.

Few of these. They cost 100x a domain test and they only need to cover the
adapter's contract, not the use cases built on top of it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.unit_of_work import SqlAlchemyUnitOfWork
from attendance.domain.note import Note

pytestmark = pytest.mark.integration


def _note(title: str, *, created: datetime) -> Note:
    return Note.create(title=title, body="body", now=created)


async def test_a_note_survives_a_round_trip_through_the_database(session: AsyncSession):
    """The mapping test. Every field written must come back — this is what
    catches a column added to the domain and forgotten in ``tables.py``."""
    uow = SqlAlchemyUnitOfWork(session)
    note = _note("Groceries", created=datetime(2026, 1, 1, tzinfo=UTC))

    async with uow:
        await uow.notes.add(note)
        await uow.commit()

    # Expire everything so the next read genuinely hits the database instead of
    # handing back the in-memory object we just added.
    session.expunge_all()
    async with uow:
        loaded = await uow.notes.get(note.id)

    assert loaded is not None
    assert loaded.id == note.id
    assert loaded.title == "Groceries"
    assert loaded.body == "body"
    assert loaded.archived_at is None
    # It comes back as a domain object with its rules intact, not as a row.
    assert isinstance(loaded, Note)
    assert not loaded.is_archived


async def test_get_returns_none_for_an_unknown_id(session: AsyncSession):
    uow = SqlAlchemyUnitOfWork(session)

    async with uow:
        assert await uow.notes.get(uuid.uuid4()) is None


async def test_list_orders_newest_first_and_hides_archived(session: AsyncSession):
    """The same contract asserted against the fake in the service tests — proving
    the two implementations actually agree."""
    uow = SqlAlchemyUnitOfWork(session)
    older = _note("Older", created=datetime(2026, 1, 1, tzinfo=UTC))
    newer = _note("Newer", created=datetime(2026, 6, 1, tzinfo=UTC))
    archived = _note("Archived", created=datetime(2026, 3, 1, tzinfo=UTC))
    archived.archive(now=datetime(2026, 3, 2, tzinfo=UTC))

    async with uow:
        for note in (older, newer, archived):
            await uow.notes.add(note)
        await uow.commit()

    async with uow:
        assert [n.title for n in await uow.notes.list()] == ["Newer", "Older"]
        assert [n.title for n in await uow.notes.list(include_archived=True)] == [
            "Newer",
            "Archived",
            "Older",
        ]


async def test_rollback_leaves_nothing_behind(session: AsyncSession):
    """The Unit of Work's whole reason to exist. If this passes with the commit
    removed, the transaction boundary is not doing anything."""
    uow = SqlAlchemyUnitOfWork(session)
    note = _note("Doomed", created=datetime(2026, 1, 1, tzinfo=UTC))

    with pytest.raises(RuntimeError):
        async with uow:
            await uow.notes.add(note)
            await uow.flush()  # the insert reaches the DB...
            raise RuntimeError("something went wrong mid-use-case")

    async with uow:
        assert await uow.notes.get(note.id) is None  # ...and is rolled back


async def test_delete_is_idempotent(session: AsyncSession):
    uow = SqlAlchemyUnitOfWork(session)

    async with uow:
        await uow.notes.delete(uuid.uuid4())  # must not raise
        await uow.commit()
