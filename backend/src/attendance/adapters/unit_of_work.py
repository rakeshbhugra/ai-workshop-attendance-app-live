"""SQLAlchemy Unit of Work — borrows a session, adds transaction semantics.

The session's *lifecycle* is owned by the caller (FastAPI's ``get_db`` yields one
per request); this class only groups the repositories and marks the commit /
rollback boundary. That split is what lets one request run two UoWs against the
same session when it genuinely needs two transactions.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.repositories.attendance import SqlAttendanceRepository
from attendance.adapters.repositories.note import SqlAlchemyNoteRepository
from attendance.adapters.repositories.user import SqlAlchemyUserRepository
from attendance.ports.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.attendance = SqlAttendanceRepository(session)
        self.notes = SqlAlchemyNoteRepository(session)
        self.users = SqlAlchemyUserRepository(session)
        self._committed = False

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Roll back on the way out of a failed block. Without this, a half-applied
        # use case would sit in the session and get committed by the *next* one.
        if exc_type is not None and not self._committed:
            await self.rollback()

    async def commit(self) -> None:
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()
