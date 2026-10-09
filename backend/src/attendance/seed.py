"""Explicit demo import: python -m attendance.seed ../mock-ui/mock-data.json.

Seed only empty attendance tables and commit the import atomically. Re-running
against the seeded database is a no-op, never overwriting staff edits.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from attendance.adapters.orm import start_mappers
from attendance.adapters.unit_of_work import SqlAlchemyUnitOfWork
from attendance.config.database import dispose_engine, get_sessionmaker
from attendance.domain.attendance import AttendanceRecord, Session, Student, Workshop
from attendance.domain.exceptions import ConflictError
from attendance.domain.user import ExternalIdentity, User


async def seed(path: Path) -> None:
    data = json.loads(await asyncio.to_thread(path.read_text))
    start_mappers()
    now = datetime.now(UTC)
    async with get_sessionmaker()() as db, SqlAlchemyUnitOfWork(db) as uow:
        existing = await uow.attendance.workshops()
        if existing:
            print("Attendance data already exists; seed skipped.")
            return
        if await uow.attendance.students():
            raise ConflictError("Seed requires an empty student roster")
        identity = ExternalIdentity("seed", "demo", "seed@example.invalid", "Demo importer", True)
        actor = User.register(identity, now)
        await uow.users.add(actor)
        await uow.flush()
        for item in data["students"]:
            await uow.attendance.save_student(Student.create(**item), new=True)
        for item in data["workshops"]:
            fields = dict(item)
            student_ids = fields.pop("studentIds")
            workshop = Workshop.create(**fields)
            await uow.attendance.save_workshop(workshop, new=True)
            await uow.attendance.enroll(workshop.id, student_ids, now)
        for item in data["sessions"]:
            s = Session.create(
                item["id"],
                item["workshopId"],
                item["title"],
                item["date"],
                item["start"],
                item["end"],
            )
            await uow.attendance.add_session(s, await uow.attendance.enrolled_ids(s.workshop_id))
        for key, item in data["attendance"].items():
            session_id, student_id = key.split(":", 1)
            record = AttendanceRecord.create(
                session_id, student_id, item["status"], item["checkIn"], item["checkOut"]
            )
            await uow.attendance.save_records([record], actor.id, now)
        await uow.commit()
        print(f"Seeded {len(data['students'])} students and {len(data['sessions'])} sessions.")
    await dispose_engine()


def main() -> None:
    asyncio.run(seed(Path(sys.argv[1] if len(sys.argv) > 1 else "../mock-ui/mock-data.json")))


if __name__ == "__main__":
    main()
