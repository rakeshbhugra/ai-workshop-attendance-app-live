"""Note entity — the worked example of a *rich* domain model.

This file is the reference for every entity you add. Three things make it work:

1. **It imports nothing external.** No SQLAlchemy, no Pydantic, no FastAPI. A
   plain dataclass. The ORM mapping lives in ``adapters/orm/tables.py`` and maps
   *onto* this class (imperative mapping), so persistence never leaks in here.
2. **The rules live on the entity, not in the service.** ``archive()`` knows a
   note can't be archived twice. The service just loads, calls, and saves. If you
   find yourself writing ``if note.archived_at is not None: raise ...`` inside a
   service, that rule belongs here.
3. **Time is passed in, never read.** ``datetime.now()`` inside a domain method
   makes the rule untestable. The caller (the service) owns the clock.

Delete this file — and its port/adapter/service/route/tests — once you have a
real entity. It exists to be copied, not kept.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from attendance.domain.exceptions import ConflictError, ValidationError

TITLE_MAX_LENGTH = 200


class BlankNoteTitle(ValidationError):
    def __init__(self) -> None:
        super().__init__("A note title cannot be blank.")


class NoteTitleTooLong(ValidationError):
    def __init__(self) -> None:
        super().__init__(f"A note title cannot exceed {TITLE_MAX_LENGTH} characters.")


class NoteAlreadyArchived(ConflictError):
    def __init__(self) -> None:
        super().__init__("This note is already archived.")


class ArchivedNoteIsReadOnly(ConflictError):
    def __init__(self) -> None:
        super().__init__("An archived note cannot be edited. Restore it first.")


@dataclass
class Note:
    title: str
    body: str
    created_at: datetime
    updated_at: datetime
    # Defaults come last so the field order stays readable; the ORM maps by name,
    # not position, so this ordering is purely for humans.
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    archived_at: datetime | None = None

    @classmethod
    def create(cls, title: str, body: str, now: datetime) -> Note:
        """The only sanctioned way to make a Note — so a Note can never exist in
        an invalid state, including one loaded from a fixture or a test."""
        title = _validated_title(title)
        return cls(title=title, body=body, created_at=now, updated_at=now)

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def edit(self, title: str, body: str, now: datetime) -> None:
        if self.is_archived:
            raise ArchivedNoteIsReadOnly
        self.title = _validated_title(title)
        self.body = body
        self.updated_at = now

    def archive(self, now: datetime) -> None:
        if self.is_archived:
            raise NoteAlreadyArchived
        self.archived_at = now
        self.updated_at = now

    def restore(self, now: datetime) -> None:
        # Deliberately tolerant: restoring an active note is a no-op rather than an
        # error, because the caller's intent ("make sure this is active") is already
        # satisfied. Archiving twice *is* an error because it would move the
        # archived_at timestamp and lose information.
        if not self.is_archived:
            return
        self.archived_at = None
        self.updated_at = now


def _validated_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise BlankNoteTitle
    if len(title) > TITLE_MAX_LENGTH:
        raise NoteTitleTooLong
    return title
