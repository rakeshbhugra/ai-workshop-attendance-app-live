"""Service tests — orchestration, with a fake Unit of Work.

What belongs here: did the use case load the right thing, call the domain, and
commit? What does *not* belong here: re-testing the business rules. That
``archive()`` twice raises is tested once, in the domain tests. Testing it again
through the service is duplication that doubles the cost of every future change.

Every assertion below is about *state* (what ended up in the fake) or *outcome*
(what was returned / raised) — never "was this method called with these
arguments". That is the difference between a fake and a mock, and it is why these
tests survive refactors.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from attendance.adapters.unit_of_work_fake import FakeUnitOfWork
from attendance.domain.note import Note, NoteAlreadyArchived
from attendance.services.notes import NoteNotFound, NoteService


async def test_create_persists_the_note_and_commits(uow: FakeUnitOfWork):
    service = NoteService(uow)

    note = await service.create(title="Groceries", body="milk")

    assert await uow.notes.get(note.id) is note
    # A service that mutates and forgets to commit is a real bug class; the fake
    # exposes the flag precisely so it can be caught here rather than in staging.
    assert uow.committed


async def test_list_hides_archived_notes_by_default(uow: FakeUnitOfWork):
    service = NoteService(uow)
    kept = await service.create(title="Kept", body="")
    archived = await service.create(title="Archived", body="")
    await service.archive(archived.id)

    visible = await service.list()

    assert [n.id for n in visible] == [kept.id]
    assert {n.id for n in await service.list(include_archived=True)} == {kept.id, archived.id}


async def test_list_returns_newest_first(uow: FakeUnitOfWork):
    # Timestamps set explicitly rather than by creating two notes in a row: back
    # to back calls can land on the same microsecond, and a stable sort would
    # then pass or fail on timing rather than on behaviour.
    older = Note.create(title="Older", body="", now=datetime(2026, 1, 1, tzinfo=UTC))
    newer = Note.create(title="Newer", body="", now=datetime(2026, 6, 1, tzinfo=UTC))
    await uow.notes.add(older)
    await uow.notes.add(newer)

    listed = await NoteService(uow).list()

    # Ordering is part of the repository contract, so both the fake and the
    # SQLAlchemy adapter are held to it (see the integration test).
    assert [n.id for n in listed] == [newer.id, older.id]


async def test_getting_an_unknown_note_raises_not_found(uow: FakeUnitOfWork):
    with pytest.raises(NoteNotFound):
        await NoteService(uow).get(uuid.uuid4())


async def test_edit_updates_the_stored_note(uow: FakeUnitOfWork):
    service = NoteService(uow)
    note = await service.create(title="Groceries", body="milk")

    await service.edit(note.id, title="Shopping", body="eggs")

    stored = await uow.notes.get(note.id)
    assert stored is not None
    assert (stored.title, stored.body) == ("Shopping", "eggs")


async def test_a_domain_rule_violation_propagates_and_does_not_commit(uow: FakeUnitOfWork):
    """The service adds no error handling of its own — the domain error travels
    up to the API layer, which is the only place that knows about status codes."""
    service = NoteService(uow)
    note = await service.create(title="Groceries", body="")
    await service.archive(note.id)
    uow.committed = False  # reset after the successful archive above

    with pytest.raises(NoteAlreadyArchived):
        await service.archive(note.id)

    assert not uow.committed


async def test_deleting_an_unknown_note_raises_rather_than_silently_succeeding(
    uow: FakeUnitOfWork,
):
    with pytest.raises(NoteNotFound):
        await NoteService(uow).delete(uuid.uuid4())


async def test_delete_removes_the_note(uow: FakeUnitOfWork):
    service = NoteService(uow)
    note = await service.create(title="Groceries", body="")

    await service.delete(note.id)

    assert await uow.notes.get(note.id) is None
