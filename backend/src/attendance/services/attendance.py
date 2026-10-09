"""Attendance use cases: transaction boundaries and domain delegation."""

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from attendance.domain.attendance import AttendanceRecord, Session, Student, Workshop
from attendance.domain.exceptions import NotFoundError, ValidationError
from attendance.ports.unit_of_work import UnitOfWork


class AttendanceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def students(self, workshop_id: str | None = None) -> list[Student]:
        async with self.uow as uow:
            return await uow.attendance.students(workshop_id)

    async def workshops(self) -> list[tuple[Workshop, list[str]]]:
        async with self.uow as uow:
            groups = await uow.attendance.enrollment_groups()
            return [(w, groups.get(w.id, [])) for w in await uow.attendance.workshops()]

    async def sessions(self, workshop_id: str | None = None) -> list[Session]:
        async with self.uow as uow:
            return await uow.attendance.sessions(workshop_id)

    async def create_student(
        self,
        name: str,
        email: str,
        college: str,
        id: str | None = None,
        workshop_id: str | None = None,
    ) -> Student:
        student = Student.create(id or f"SN-{uuid4().hex[:12]}", name, email, college)
        async with self.uow as uow:
            if workshop_id and await uow.attendance.workshop(workshop_id) is None:
                raise NotFoundError("Workshop not found")
            await uow.attendance.save_student(student, new=True)
            if workshop_id:
                ids = await uow.attendance.enrolled_ids(workshop_id)
                await uow.attendance.enroll(workshop_id, [*ids, student.id], datetime.now(UTC))
            await uow.commit()
        return student

    async def update_student(self, id: str, changes: dict[str, str | bool]) -> Student:
        async with self.uow as uow:
            old = await uow.attendance.student(id)
            if old is None:
                raise NotFoundError("Student not found")
            data = asdict(old) | changes
            student = Student.create(**data)
            await uow.attendance.save_student(student)
            if not student.active:
                for workshop in await uow.attendance.workshops():
                    ids = await uow.attendance.enrolled_ids(workshop.id)
                    if student.id in ids:
                        await uow.attendance.enroll(
                            workshop.id,
                            [sid for sid in ids if sid != student.id],
                            datetime.now(UTC),
                        )
            await uow.commit()
            return student

    async def create_workshop(self, workshop: Workshop, student_ids: list[str]) -> Workshop:
        async with self.uow as uow:
            await self._validate_students(student_ids)
            await uow.attendance.save_workshop(workshop, new=True)
            await uow.attendance.enroll(workshop.id, student_ids, datetime.now(UTC))
            await uow.commit()
            return workshop

    async def enroll(self, workshop_id: str, student_ids: list[str]) -> list[str]:
        async with self.uow as uow:
            if await uow.attendance.workshop(workshop_id) is None:
                raise NotFoundError("Workshop not found")
            await self._validate_students(student_ids)
            await uow.attendance.enroll(workshop_id, student_ids, datetime.now(UTC))
            await uow.commit()
            return sorted(student_ids)

    async def _validate_students(self, student_ids: list[str]) -> None:
        known = {s.id for s in await self.uow.attendance.students() if s.active}
        if len(set(student_ids)) != len(student_ids):
            raise ValidationError("Duplicate students in enrollment")
        if not set(student_ids) <= known:
            raise NotFoundError("Student not found")

    async def create_session(self, session: Session) -> Session:
        async with self.uow as uow:
            if await uow.attendance.workshop(session.workshop_id) is None:
                raise NotFoundError("Workshop not found")
            enrolled = await uow.attendance.students(session.workshop_id)
            await uow.attendance.add_session(session, [s.id for s in enrolled if s.active])
            await uow.commit()
            return session

    async def records(self, session_id: str) -> list[AttendanceRecord]:
        async with self.uow as uow:
            if await uow.attendance.session(session_id) is None:
                raise NotFoundError("Session not found")
            return await uow.attendance.records(session_id)

    async def mark(
        self, session_id: str, records: list[AttendanceRecord], actor: UUID
    ) -> list[AttendanceRecord]:
        async with self.uow as uow:
            if await uow.attendance.session(session_id) is None:
                raise NotFoundError("Session not found")
            roster = set(await uow.attendance.roster(session_id))
            ids = [r.student_id for r in records]
            if len(ids) != len(set(ids)):
                raise ValidationError("Duplicate students in attendance update")
            if not set(ids) <= roster or any(r.session_id != session_id for r in records):
                raise ValidationError("Student is not on this session's roster")
            await uow.attendance.save_records(records, actor, datetime.now(UTC))
            await uow.commit()
            return await uow.attendance.records(session_id)
