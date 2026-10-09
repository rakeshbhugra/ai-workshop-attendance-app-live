"""Mock-compatible camelCase DTOs mapped explicitly from domain entities."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from attendance.domain.attendance import AttendanceRecord, Session, Student, Workshop


class StudentIn(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    college: str = Field(default="", max_length=240)
    workshopId: str | None = None


class StudentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", min_length=1, max_length=200)
    email: str = Field(default="", min_length=3, max_length=320)
    college: str = Field(default="", max_length=240)
    active: bool = True


class StudentOut(BaseModel):
    id: str
    name: str
    email: str
    college: str
    active: bool

    @classmethod
    def of(cls, s: Student) -> StudentOut:
        return cls(id=s.id, name=s.name, email=s.email, college=s.college, active=s.active)


class EnrollmentIn(BaseModel):
    studentIds: list[str] = Field(default_factory=list, max_length=10000)


class WorkshopIn(EnrollmentIn):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    category: str = Field(default="", max_length=200)
    facilitator: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    dates: str = Field(default="", max_length=200)
    days: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=240)
    active: bool = True

    def domain(self) -> Workshop:
        return Workshop.create(**self.model_dump(exclude={"studentIds"}))


class WorkshopOut(WorkshopIn):
    @classmethod
    def of(cls, w: Workshop, ids: list[str]) -> WorkshopOut:
        return cls(
            id=w.id,
            title=w.title,
            description=w.description,
            category=w.category,
            facilitator=w.facilitator,
            email=w.email,
            dates=w.dates,
            days=w.days,
            location=w.location,
            active=w.active,
            studentIds=ids,
        )


class SessionIn(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    workshopId: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(default="Asia/Kolkata", max_length=80)

    def domain(self) -> Session:
        return Session.create(
            self.id, self.workshopId, self.title, self.date, self.start, self.end, self.timezone
        )

    @classmethod
    def of(cls, s: Session) -> SessionIn:
        return cls(
            id=s.id,
            workshopId=s.workshop_id,
            title=s.title,
            date=s.date,
            start=s.start,
            end=s.end,
            timezone=s.timezone,
        )


class RecordIn(BaseModel):
    studentId: str = Field(min_length=1, max_length=80)
    status: str = Field(pattern="^(unmarked|present|absent)$")
    checkIn: str = Field(default="", pattern=r"^(|\d{2}:\d{2})$")
    checkOut: str = Field(default="", pattern=r"^(|\d{2}:\d{2})$")

    def domain(self, session_id: str) -> AttendanceRecord:
        return AttendanceRecord.create(
            session_id, self.studentId, self.status, self.checkIn, self.checkOut
        )

    @classmethod
    def of(cls, r: AttendanceRecord) -> RecordIn:
        return cls(
            studentId=r.student_id, status=r.status, checkIn=r.check_in, checkOut=r.check_out
        )


class AttendanceIn(BaseModel):
    records: list[RecordIn] = Field(max_length=10000)
