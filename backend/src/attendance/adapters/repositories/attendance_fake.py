"""In-memory implementation preserving SQL ordering and roster semantics."""

from datetime import datetime
from uuid import UUID

from attendance.domain.attendance import AttendanceRecord, Session, Student, Workshop
from attendance.domain.exceptions import ConflictError
from attendance.ports.attendance import AttendanceRepository


class FakeAttendanceRepository(AttendanceRepository):
    def __init__(self) -> None:
        self.student_data: dict[str, Student] = {}
        self.workshop_data: dict[str, Workshop] = {}
        self.session_data: dict[str, Session] = {}
        self.enrollment_data: dict[str, list[str]] = {}
        self.roster_data: dict[str, list[str]] = {}
        self.record_data: dict[tuple[str, str], AttendanceRecord] = {}
        self.audit: list[tuple[AttendanceRecord, UUID, datetime]] = []

    async def students(self, workshop_id: str | None = None) -> list[Student]:
        return sorted(
            [
                s
                for s in self.student_data.values()
                if workshop_id is None or s.id in self.enrollment_data.get(workshop_id, [])
            ],
            key=lambda s: (s.name, s.id),
        )

    async def student(self, student_id: str) -> Student | None:
        return self.student_data.get(student_id)

    async def save_student(self, student: Student, *, new: bool = False) -> None:
        if (new and student.id in self.student_data) or any(
            s.email == student.email and s.id != student.id for s in self.student_data.values()
        ):
            raise ConflictError("Student identifier or email already exists")
        self.student_data[student.id] = student

    async def workshops(self) -> list[Workshop]:
        return sorted(self.workshop_data.values(), key=lambda w: w.title)

    async def enrollment_groups(self) -> dict[str, list[str]]:
        return {key: sorted(ids) for key, ids in self.enrollment_data.items()}

    async def workshop(self, workshop_id: str) -> Workshop | None:
        return self.workshop_data.get(workshop_id)

    async def save_workshop(self, workshop: Workshop, *, new: bool = False) -> None:
        if new and workshop.id in self.workshop_data:
            raise ConflictError("Workshop identifier already exists")
        self.workshop_data[workshop.id] = workshop

    async def enrolled_ids(self, workshop_id: str) -> list[str]:
        return sorted(self.enrollment_data.get(workshop_id, []))

    async def enroll(self, workshop_id: str, student_ids: list[str], now: datetime) -> None:
        self.enrollment_data[workshop_id] = list(student_ids)
        for session in self.session_data.values():
            if session.workshop_id == workshop_id and session.is_upcoming(now):
                saved = {
                    r.student_id
                    for r in await self.records(session.id)
                    if r.status != "unmarked" or r.check_in or r.check_out
                }
                self.roster_data[session.id] = sorted(saved | set(student_ids))

    async def sessions(self, workshop_id: str | None = None) -> list[Session]:
        return sorted(
            [
                s
                for s in self.session_data.values()
                if workshop_id is None or s.workshop_id == workshop_id
            ],
            key=lambda s: (s.date, s.start, s.id),
        )

    async def session(self, session_id: str) -> Session | None:
        return self.session_data.get(session_id)

    async def add_session(self, session: Session, student_ids: list[str]) -> None:
        if session.id in self.session_data:
            raise ConflictError("Session identifier already exists")
        self.session_data[session.id] = session
        self.roster_data[session.id] = list(student_ids)

    async def roster(self, session_id: str) -> list[str]:
        return sorted(self.roster_data.get(session_id, []))

    async def records(self, session_id: str) -> list[AttendanceRecord]:
        return [
            self.record_data.get((session_id, sid), AttendanceRecord(session_id, sid))
            for sid in await self.roster(session_id)
        ]

    async def save_records(
        self, records: list[AttendanceRecord], actor: UUID, now: datetime
    ) -> None:
        for record in records:
            self.record_data[(record.session_id, record.student_id)] = record
            self.audit.append((record, actor, now))
