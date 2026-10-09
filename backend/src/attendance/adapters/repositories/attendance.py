"""SQL collections, with transaction locking for roster and attendance edits."""

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.orm import attendance_tables as t
from attendance.adapters.repositories.attendance_sessions import SqlSessionCollections
from attendance.domain.attendance import Session, Student, Workshop
from attendance.domain.exceptions import ConflictError
from attendance.ports.attendance import AttendanceRepository


class SqlAttendanceRepository(SqlSessionCollections, AttendanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def students(self, workshop_id: str | None = None) -> list[Student]:
        q = select(t.students)
        if workshop_id is not None:
            q = q.join(t.enrollments).where(t.enrollments.c.workshop_id == workshop_id)
        return [
            Student(**dict(row))
            for row in (
                await self.db.execute(q.order_by(t.students.c.name, t.students.c.id))
            ).mappings()
        ]

    async def student(self, student_id: str) -> Student | None:
        row = (
            (await self.db.execute(select(t.students).where(t.students.c.id == student_id)))
            .mappings()
            .first()
        )
        return Student(**dict(row)) if row else None

    async def save_student(self, student: Student, *, new: bool = False) -> None:
        try:
            q = (
                insert(t.students).values(**asdict(student))
                if new
                else update(t.students)
                .where(t.students.c.id == student.id)
                .values(**asdict(student))
            )
            await self.db.execute(q)
        except IntegrityError as error:
            raise ConflictError("Student identifier or email already exists") from error

    async def workshops(self) -> list[Workshop]:
        return [
            Workshop(**dict(row))
            for row in (
                await self.db.execute(select(t.workshops).order_by(t.workshops.c.title))
            ).mappings()
        ]

    async def enrollment_groups(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        rows = (
            await self.db.execute(select(t.enrollments).order_by(t.enrollments.c.student_id))
        ).mappings()
        for row in rows:
            groups.setdefault(str(row["workshop_id"]), []).append(str(row["student_id"]))
        return groups

    async def workshop(self, workshop_id: str) -> Workshop | None:
        row = (
            (await self.db.execute(select(t.workshops).where(t.workshops.c.id == workshop_id)))
            .mappings()
            .first()
        )
        return Workshop(**dict(row)) if row else None

    async def save_workshop(self, workshop: Workshop, *, new: bool = False) -> None:
        try:
            q = (
                insert(t.workshops).values(**asdict(workshop))
                if new
                else update(t.workshops)
                .where(t.workshops.c.id == workshop.id)
                .values(**asdict(workshop))
            )
            await self.db.execute(q)
        except IntegrityError as error:
            raise ConflictError("Workshop identifier already exists") from error

    async def enrolled_ids(self, workshop_id: str) -> list[str]:
        return list(
            (
                await self.db.scalars(
                    select(t.enrollments.c.student_id)
                    .where(t.enrollments.c.workshop_id == workshop_id)
                    .order_by(t.enrollments.c.student_id)
                )
            ).all()
        )

    async def enroll(self, workshop_id: str, student_ids: list[str], now: datetime) -> None:
        await self.db.execute(
            select(t.workshops.c.id).where(t.workshops.c.id == workshop_id).with_for_update()
        )
        await self.db.execute(
            delete(t.enrollments).where(t.enrollments.c.workshop_id == workshop_id)
        )
        if student_ids:
            await self.db.execute(
                insert(t.enrollments),
                [{"workshop_id": workshop_id, "student_id": sid} for sid in student_ids],
            )
        # Retain existing rosters: removing an enrollment must not erase history.
        # Newly enrolled students are added only to sessions on future dates.
        rows = (
            await self.db.execute(
                select(t.sessions).where(t.sessions.c.workshop_id == workshop_id).with_for_update()
            )
        ).mappings()
        future = [Session(**dict(row)) for row in rows]
        future = [s for s in future if s.is_upcoming(now)]
        for session in future:
            session_id = session.id
            saved = {
                r.student_id
                for r in await self.records(session_id)
                if r.status != "unmarked" or r.check_in or r.check_out
            }
            previous = set(await self.roster(session_id))
            removed = previous - set(student_ids) - saved
            if removed:
                await self.db.execute(
                    delete(t.records).where(
                        t.records.c.session_id == session_id, t.records.c.student_id.in_(removed)
                    )
                )
                await self.db.execute(
                    delete(t.roster).where(
                        t.roster.c.session_id == session_id, t.roster.c.student_id.in_(removed)
                    )
                )
            additions = [
                {"session_id": session_id, "student_id": sid}
                for sid in student_ids
                if sid not in previous
            ]
            if additions:
                await self.db.execute(insert(t.roster), additions)
