from datetime import UTC, datetime
from uuid import uuid4

import pytest

from attendance.adapters.repositories.attendance import SqlAttendanceRepository
from attendance.domain.attendance import Session, Student, Workshop
from attendance.domain.exceptions import ConflictError


@pytest.mark.integration
async def test_sql_collection_contract(session):
    repo = SqlAttendanceRepository(session)
    assert await repo.student("missing") is None
    assert await repo.workshop("missing") is None
    assert await repo.session("missing") is None
    await repo.save_student(Student.create("A", "Alice", "alice@example.com", ""), new=True)
    await repo.save_student(Student.create("A", "Updated", "alice@example.com", ""))
    await repo.save_workshop(Workshop.create("w", "Workshop"), new=True)
    await repo.save_workshop(Workshop.create("w", "Updated"))
    assert (await repo.workshop("w")).title == "Updated"
    await repo.enroll("w", ["A"], datetime(2026, 1, 1, tzinfo=UTC))
    s = Session.create("s", "w", "Title", "2099-01-01", "10:00", "12:00")
    await repo.add_session(s, ["A"])
    await session.commit()
    assert (await repo.students())[0].name == "Updated"
    assert (await repo.sessions())[0].id == "s"
    await repo.save_records([], uuid4(), datetime.now(UTC))
    with pytest.raises(ConflictError):
        await repo.save_student(Student.create("B", "Bob", "alice@example.com", ""), new=True)
    await session.rollback()
    with pytest.raises(ConflictError):
        await repo.save_workshop(Workshop.create("w", "Duplicate"), new=True)
    await session.rollback()
    with pytest.raises(ConflictError):
        await repo.add_session(s, [])
    await session.rollback()
