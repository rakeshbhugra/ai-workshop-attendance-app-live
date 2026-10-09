"""In-memory repositories for service tests.

These are **fakes**, not mocks: real working implementations of the port, backed
by a dict instead of Postgres. A test asserts on the state they end up in
(``uow.notes._notes``), never on which methods were called. That distinction is
why service tests here don't break every time you refactor a service's internals.

Rule: a fake must obey the same contract as the real adapter. If
``SqlAlchemyNoteRepository.list()`` is newest-first, so is this one — otherwise
green service tests will hide a bug that only shows up in production.
"""

from __future__ import annotations

import uuid

from attendance.domain.note import Note
from attendance.domain.user import Identity, User
from attendance.ports.repositories import NoteRepository, UserRepository


class FakeNoteRepository(NoteRepository):
    def __init__(self) -> None:
        self._notes: dict[uuid.UUID, Note] = {}

    async def add(self, note: Note) -> None:
        self._notes[note.id] = note

    async def get(self, note_id: uuid.UUID) -> Note | None:
        return self._notes.get(note_id)

    async def list(self, *, include_archived: bool = False) -> list[Note]:
        notes = list(self._notes.values())
        if not include_archived:
            notes = [n for n in notes if not n.is_archived]
        return sorted(notes, key=lambda n: n.created_at, reverse=True)

    async def delete(self, note_id: uuid.UUID) -> None:
        self._notes.pop(note_id, None)


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, User] = {}
        self.identities: dict[tuple[str, str], uuid.UUID] = {}

    async def add(self, user: User) -> None:
        self.items[user.id] = user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return self.items.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        matches = [u for u in self.items.values() if u.email.lower() == email.lower()]
        return min(matches, key=lambda u: u.created_at, default=None)

    async def get_by_identity(self, provider: str, subject: str) -> User | None:
        user_id = self.identities.get((provider, subject))
        return self.items.get(user_id) if user_id else None

    async def link(self, identity: Identity) -> None:
        self.identities[(identity.provider, identity.subject)] = identity.user_id
