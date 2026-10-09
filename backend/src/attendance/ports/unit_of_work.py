"""Port — the Unit of Work owns a transaction and exposes every repository.

One logical operation = one commit or one rollback. Services take a UoW, not a
session and not a repository, so that a use case touching three repositories
still lands atomically.

Add a repository to an app by declaring it here, then implementing it in both
``adapters/unit_of_work.py`` (SQLAlchemy) and ``adapters/unit_of_work_fake.py``
(in-memory). Declaring it in one and not the other is the mistake to watch for;
mypy catches it because both subclass this ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from attendance.ports.attendance import AttendanceRepository
from attendance.ports.repositories import NoteRepository, UserRepository


class UnitOfWork(ABC):
    attendance: AttendanceRepository
    notes: NoteRepository
    users: UserRepository

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Rolls back on an exception. Commit is always explicit — forgetting to
        commit loses the write, which is the safe direction to fail in."""

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None:
        """Push pending inserts to the DB (assigning FKs and defaults) without
        ending the transaction. Needed when a later step in the same use case
        depends on a generated value."""
