"""Workshop attendance invariants, independent of transport and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from attendance.domain.exceptions import ValidationError


def required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} cannot be blank")
    return value


@dataclass
class Student:
    id: str
    name: str
    email: str
    college: str
    active: bool = True

    @classmethod
    def create(cls, id: str, name: str, email: str, college: str, active: bool = True) -> Student:
        email = required(email, "Email").lower()
        if "@" not in email or not all(email.split("@", 1)):
            raise ValidationError("A valid email is required")
        return cls(
            required(id, "Student ID"), required(name, "Name"), email, college.strip(), active
        )


@dataclass
class Workshop:
    id: str
    title: str
    description: str = ""
    category: str = ""
    facilitator: str = ""
    email: str = ""
    dates: str = ""
    days: str = ""
    location: str = ""
    active: bool = True

    @classmethod
    def create(cls, id: str, title: str, **fields: str | bool) -> Workshop:
        item = cls(required(id, "Workshop ID"), required(title, "Title"))
        for key, value in fields.items():
            if key not in {"id", "title"} and hasattr(item, key):
                setattr(item, key, value)
        return item


@dataclass
class Session:
    id: str
    workshop_id: str
    title: str
    date: str
    start: str
    end: str
    timezone: str = "Asia/Kolkata"

    def is_upcoming(self, now: datetime) -> bool:
        start = datetime.combine(
            date.fromisoformat(self.date), time.fromisoformat(self.start), ZoneInfo(self.timezone)
        )
        return start > now

    @classmethod
    def create(
        cls,
        id: str,
        workshop_id: str,
        title: str,
        day: str,
        start: str,
        end: str,
        timezone: str = "Asia/Kolkata",
    ) -> Session:
        try:
            date.fromisoformat(day)
            begin, finish = time.fromisoformat(start), time.fromisoformat(end)
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValidationError("Invalid session date, time or timezone") from error
        if finish <= begin:
            raise ValidationError("Session end must be after start on the same day")
        return cls(
            required(id, "Session ID"),
            required(workshop_id, "Workshop ID"),
            required(title, "Title"),
            day,
            start,
            end,
            timezone,
        )


@dataclass
class AttendanceRecord:
    session_id: str
    student_id: str
    status: str = "unmarked"
    check_in: str = ""
    check_out: str = ""

    @classmethod
    def create(
        cls,
        session_id: str,
        student_id: str,
        status: str = "unmarked",
        check_in: str = "",
        check_out: str = "",
    ) -> AttendanceRecord:
        if status not in {"unmarked", "present", "absent"}:
            raise ValidationError("Invalid attendance status")
        try:
            begin = time.fromisoformat(check_in) if check_in else None
            finish = time.fromisoformat(check_out) if check_out else None
        except ValueError as error:
            raise ValidationError("Invalid participation time") from error
        if finish and not begin:
            raise ValidationError("Check-in is required before check-out")
        if begin and finish and finish < begin:
            raise ValidationError("Check-out cannot precede check-in")
        if status != "present" and (begin or finish):
            raise ValidationError("Participation times require Present attendance")
        return cls(session_id, student_id, status, check_in, check_out)

    def duration_minutes(self) -> int | None:
        if not self.check_in or not self.check_out:
            return None
        day = date(2000, 1, 1)
        begin = datetime.combine(day, time.fromisoformat(self.check_in))
        finish = datetime.combine(day, time.fromisoformat(self.check_out))
        return int((finish - begin).total_seconds() // 60)
