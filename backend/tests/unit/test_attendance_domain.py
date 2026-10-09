from datetime import UTC, datetime

import pytest

from attendance.domain.attendance import AttendanceRecord, Session, Student, Workshop
from attendance.domain.exceptions import ValidationError


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "late"},
        {"status": "present", "check_in": "25:00"},
        {"status": "present", "check_out": "11:00"},
        {"status": "present", "check_in": "11:00", "check_out": "10:00"},
        {"status": "absent", "check_in": "10:00"},
    ],
)
def test_invalid_participation(fields):
    with pytest.raises(ValidationError):
        AttendanceRecord.create("session", "student", **fields)


def test_duration_distinguishes_missing_data():
    assert AttendanceRecord.create("s", "p", "present").duration_minutes() is None
    assert AttendanceRecord.create("s", "p", "present", "10:00", "11:45").duration_minutes() == 105
    assert AttendanceRecord.create("s", "p", "present", "10:00", "10:00").duration_minutes() == 0


@pytest.mark.parametrize("name,email", [(" ", "a@b.com"), ("A", "invalid"), ("A", "@b")])
def test_invalid_student(name, email):
    with pytest.raises(ValidationError):
        Student.create("ID", name, email, "college")


def test_student_normalizes_identity():
    student = Student.create(" ID ", " Alice ", "ALICE@EXAMPLE.COM", " College ")
    assert (student.id, student.name, student.email, student.college) == (
        "ID",
        "Alice",
        "alice@example.com",
        "College",
    )
    assert Workshop.create("workshop", " Workshop ", active=False).title == "Workshop"


@pytest.mark.parametrize(
    "day,start,end,zone",
    [
        ("bad", "10:00", "12:00", "Asia/Kolkata"),
        ("2026-10-09", "25:00", "12:00", "Asia/Kolkata"),
        ("2026-10-09", "12:00", "10:00", "Asia/Kolkata"),
        ("2026-10-09", "10:00", "12:00", "Missing/Zone"),
    ],
)
def test_invalid_session(day, start, end, zone):
    with pytest.raises(ValidationError):
        Session.create("id", "workshop", "title", day, start, end, zone)


def test_upcoming_uses_session_timezone():
    session = Session.create("id", "workshop", "title", "2026-10-09", "10:00", "12:00")
    assert session.is_upcoming(datetime(2026, 10, 9, 4, 0, tzinfo=UTC))
    assert not session.is_upcoming(datetime(2026, 10, 9, 5, 0, tzinfo=UTC))
