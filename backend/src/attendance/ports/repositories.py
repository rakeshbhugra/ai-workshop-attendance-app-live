"""Ports — abstract repository contracts. Imports domain only.

A port is the *shape of the hole*; an adapter is the *plug*. Keeping them in
separate packages makes the abstract surface of the app visible in one place: if
it isn't listed here, no service can depend on it.

One repository per **aggregate root**, not per table. ``NoteRepository`` would
also own a note's comments/attachments if it had them — you would never add a
``CommentRepository`` that hands out comments detached from their note.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from attendance.domain.note import Note
from attendance.domain.user import Identity, User


class NoteRepository(ABC):
    """Collection-shaped abstraction over storage. Note the vocabulary: ``add``
    and ``get``, not ``insert`` and ``select`` — a repository pretends to be a
    set of domain objects, and the SQL is an implementation detail of one adapter.
    """

    @abstractmethod
    async def add(self, note: Note) -> None:
        """Put a note in the collection. No commit — the Unit of Work owns that."""

    @abstractmethod
    async def get(self, note_id: uuid.UUID) -> Note | None:
        """The note, or None. Returning None (not raising) keeps the 'does this
        exist?' decision with the caller, which knows what it means."""

    @abstractmethod
    async def list(self, *, include_archived: bool = False) -> list[Note]:
        """Newest first. Filtering lives here rather than in the service so the
        database does the work instead of Python."""

    @abstractmethod
    async def delete(self, note_id: uuid.UUID) -> None:
        """Idempotent: deleting an absent id is not an error."""


class UserRepository(ABC):
    """Users and the provider identities linked to them."""

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def get(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Case-insensitive. The oldest match if several share the address."""

    @abstractmethod
    async def get_by_identity(self, provider: str, subject: str) -> User | None: ...

    @abstractmethod
    async def link(self, identity: Identity) -> None: ...
