from datetime import UTC, datetime
from uuid import uuid4

import pytest

from attendance.adapters.unit_of_work_fake import FakeUnitOfWork
from attendance.domain.attendance import AttendanceRecord, Session, Workshop
from attendance.domain.exceptions import ConflictError, NotFoundError, ValidationError
from attendance.services.attendance import AttendanceService


@pytest.fixture
async def setup(uow: FakeUnitOfWork):
    service = AttendanceService(uow)
    await service.create_student("Alice", "alice@example.com", "College", "A")
    await service.create_student("Bob", "bob@example.com", "College", "B")
    await service.create_workshop(Workshop.create("w", "Workshop"), ["A", "B"])
    past = Session.create("past", "w", "Past", "2000-01-01", "10:00", "12:00")
    future = Session.create("future", "w", "Future", "2099-01-01", "10:00", "12:00")
    await service.create_session(past)
    await service.create_session(future)
    return service


async def test_archive_preserves_history_removes_future(setup, uow):
    await setup.mark("past", [AttendanceRecord.create("past", "A", "present")], uuid4())
    await setup.update_student("A", {"active": False})
    assert [r.student_id for r in await setup.records("past")] == ["A", "B"]
    assert [r.student_id for r in await setup.records("future")] == ["B"]
    assert (await setup.records("past"))[0].status == "present"
    assert (await setup.students())[0].active is False
    assert uow.committed


async def test_recorded_future_attendance_retained(setup):
    await setup.mark("future", [AttendanceRecord.create("future", "A", "absent")], uuid4())
    await setup.enroll("w", ["B"])
    assert (await setup.records("future"))[0].status == "absent"


async def test_new_student_added_to_future_only(setup):
    student = await setup.create_student("Cara", "cara@example.com", "College", workshop_id="w")
    assert student.id.startswith("SN-")
    assert len(await setup.records("past")) == 2
    assert len(await setup.records("future")) == 3
    assert len(await setup.students("w")) == 3
    assert (await setup.workshops())[0][1] == sorted(["A", "B", student.id])
    assert len(await setup.sessions("w")) == 2


@pytest.mark.parametrize("operation", ["student", "workshop", "session", "records", "mark"])
async def test_missing_entities(setup, operation):
    with pytest.raises(NotFoundError):
        if operation == "student":
            await setup.update_student("missing", {"active": False})
        elif operation == "workshop":
            await setup.enroll("missing", [])
        elif operation == "session":
            await setup.create_session(
                Session.create("missing", "missing", "Title", "2099-01-01", "10:00", "12:00")
            )
        elif operation == "records":
            await setup.records("missing")
        else:
            await setup.mark("missing", [], uuid4())


async def test_enrollment_and_attendance_integrity(setup):
    with pytest.raises(NotFoundError):
        await setup.create_student("X", "x@example.com", "", workshop_id="missing")
    with pytest.raises(NotFoundError):
        await setup.enroll("w", ["unknown"])
    with pytest.raises(ValidationError):
        await setup.enroll("w", ["A", "A"])
    with pytest.raises(ValidationError):
        await setup.mark("past", [AttendanceRecord.create("past", "unknown")], uuid4())
    with pytest.raises(ValidationError):
        await setup.mark("past", [AttendanceRecord.create("past", "A")] * 2, uuid4())
    with pytest.raises(ValidationError):
        await setup.mark("past", [AttendanceRecord.create("future", "A")], uuid4())
    with pytest.raises(ConflictError):
        await setup.create_student("Alice", "other@example.com", "", "A")
    with pytest.raises(ConflictError):
        await setup.create_student("Alice", "alice@example.com", "", "other")
    with pytest.raises(ConflictError):
        await setup.create_workshop(Workshop.create("w", "Workshop"), [])
    with pytest.raises(ConflictError):
        await setup.create_session((await setup.sessions())[0])


async def test_fake_collection_contract(setup, uow):
    assert await uow.attendance.student("missing") is None
    assert await uow.attendance.workshop("missing") is None
    assert await uow.attendance.session("missing") is None
    assert await uow.attendance.roster("missing") == []
    await uow.attendance.save_workshop(Workshop.create("w", "Updated"))
    assert (await setup.workshops())[0][0].title == "Updated"
    await uow.attendance.enroll("w", ["B"], datetime(1999, 1, 1, tzinfo=UTC))
    assert await uow.attendance.roster("past") == ["B"]
