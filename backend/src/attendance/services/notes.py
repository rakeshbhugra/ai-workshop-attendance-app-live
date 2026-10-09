"""Application service — one method per use case.

The shape of every method here is the same three beats:

    load  →  delegate to the domain  →  save

Notice what is *absent*: no ``if note.archived_at is not None: raise``. That rule
lives on the entity. When a service starts growing conditionals about an
entity's state, the logic has leaked out of the domain and should move back.

Notice also what the service *does* own: the clock, the transaction boundary, and
the "does this exist?" decision. Those are orchestration concerns, not business
rules, and the domain is better off not knowing about them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from attendance.domain.exceptions import NotFoundError
from attendance.domain.note import Note
from attendance.ports.unit_of_work import UnitOfWork


class NoteNotFound(NotFoundError):
    def __init__(self, note_id: uuid.UUID) -> None:
        super().__init__(f"No note with id {note_id}.")


class NoteService:
    def __init__(self, uow: UnitOfWork) -> None:
        # A port, never a session and never a concrete repository. This is the
        # line that makes the service testable with FakeUnitOfWork.
        self._uow = uow

    async def create(self, title: str, body: str) -> Note:
        async with self._uow as uow:
            note = Note.create(title=title, body=body, now=_now())
            await uow.notes.add(note)
            await uow.commit()
            return note

    async def list(self, *, include_archived: bool = False) -> list[Note]:
        async with self._uow as uow:
            return await uow.notes.list(include_archived=include_archived)

    async def get(self, note_id: uuid.UUID) -> Note:
        async with self._uow as uow:
            return await self._require(uow, note_id)

    async def edit(self, note_id: uuid.UUID, title: str, body: str) -> Note:
        async with self._uow as uow:
            note = await self._require(uow, note_id)
            note.edit(title=title, body=body, now=_now())
            await uow.commit()
            return note

    async def archive(self, note_id: uuid.UUID) -> Note:
        async with self._uow as uow:
            note = await self._require(uow, note_id)
            note.archive(now=_now())
            await uow.commit()
            return note

    async def restore(self, note_id: uuid.UUID) -> Note:
        async with self._uow as uow:
            note = await self._require(uow, note_id)
            note.restore(now=_now())
            await uow.commit()
            return note

    async def delete(self, note_id: uuid.UUID) -> None:
        async with self._uow as uow:
            await self._require(uow, note_id)  # 404 rather than a silent no-op
            await uow.notes.delete(note_id)
            await uow.commit()

    @staticmethod
    async def _require(uow: UnitOfWork, note_id: uuid.UUID) -> Note:
        """The repository returns None; turning that into a 404 is a use-case
        decision, so it happens here rather than in the adapter."""
        note = await uow.notes.get(note_id)
        if note is None:
            raise NoteNotFound(note_id)
        return note


def _now() -> datetime:
    """Timezone-aware, always UTC. The domain takes time as an argument so its
    rules stay testable; this is the one place that actually reads a clock."""
    return datetime.now(UTC)
