"""In-memory Unit of Work for service tests — no database, no I/O, no event loop
waiting on anything.

``committed`` is exposed so a service test can assert the use case actually
committed. That is a real behavioural assertion, not a mock spy: a service that
mutates an entity and forgets to commit is a bug this catches for free.
"""

from __future__ import annotations

from types import TracebackType

from attendance.adapters.repositories.attendance_fake import FakeAttendanceRepository
from attendance.adapters.repositories.fakes import FakeNoteRepository, FakeUserRepository
from attendance.ports.unit_of_work import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.attendance = FakeAttendanceRepository()
        self.notes = FakeNoteRepository()
        self.users = FakeUserRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None and not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def flush(self) -> None:
        return None
