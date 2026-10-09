"""SQLAlchemy implementation of NoteRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.orm.tables import note_table
from attendance.domain.note import Note
from attendance.ports.repositories import NoteRepository


class SqlAlchemyNoteRepository(NoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, note: Note) -> None:
        # No await and no commit: this only stages the insert in the session's
        # identity map. The Unit of Work decides when it hits the database.
        self._session.add(note)

    async def get(self, note_id: uuid.UUID) -> Note | None:
        stmt = select(Note).where(note_table.c.id == note_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, *, include_archived: bool = False) -> list[Note]:
        stmt = select(Note).order_by(note_table.c.created_at.desc())
        if not include_archived:
            stmt = stmt.where(note_table.c.archived_at.is_(None))
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete(self, note_id: uuid.UUID) -> None:
        await self._session.execute(delete(note_table).where(note_table.c.id == note_id))
