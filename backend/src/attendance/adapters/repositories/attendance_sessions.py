"""Session snapshots and attendance persistence, used by the aggregate repository."""

import json
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.orm import attendance_tables as t
from attendance.domain.attendance import AttendanceRecord, Session
from attendance.domain.exceptions import ConflictError


class SqlSessionCollections:
    db: AsyncSession

    async def sessions(self, workshop_id: str | None = None) -> list[Session]:
        q = select(t.sessions)
        if workshop_id is not None:
            q = q.where(t.sessions.c.workshop_id == workshop_id)
        return [
            Session(**dict(row))
            for row in (
                await self.db.execute(
                    q.order_by(t.sessions.c.date, t.sessions.c.start, t.sessions.c.id)
                )
            ).mappings()
        ]

    async def session(self, session_id: str) -> Session | None:
        row = (
            (
                await self.db.execute(
                    select(t.sessions).where(t.sessions.c.id == session_id).with_for_update()
                )
            )
            .mappings()
            .first()
        )
        return Session(**dict(row)) if row else None

    async def add_session(self, session: Session, student_ids: list[str]) -> None:
        try:
            await self.db.execute(insert(t.sessions).values(**asdict(session)))
            if student_ids:
                await self.db.execute(
                    insert(t.roster),
                    [{"session_id": session.id, "student_id": sid} for sid in student_ids],
                )
        except IntegrityError as error:
            raise ConflictError("Session identifier already exists") from error

    async def roster(self, session_id: str) -> list[str]:
        return list(
            (
                await self.db.scalars(
                    select(t.roster.c.student_id)
                    .where(t.roster.c.session_id == session_id)
                    .order_by(t.roster.c.student_id)
                )
            ).all()
        )

    async def records(self, session_id: str) -> list[AttendanceRecord]:
        rows = (
            await self.db.execute(select(t.records).where(t.records.c.session_id == session_id))
        ).mappings()
        saved = {str(row["student_id"]): AttendanceRecord(**dict(row)) for row in rows}
        return [
            saved.get(sid, AttendanceRecord(session_id, sid))
            for sid in await self.roster(session_id)
        ]

    async def save_records(
        self, records: list[AttendanceRecord], actor: UUID, now: datetime
    ) -> None:
        if not records:
            return
        old = {r.student_id: r for r in await self.records(records[0].session_id)}
        for record in records:
            previous = old[record.student_id]
            await self.db.execute(
                delete(t.records).where(
                    t.records.c.session_id == record.session_id,
                    t.records.c.student_id == record.student_id,
                )
            )
            await self.db.execute(insert(t.records).values(**asdict(record)))
            await self.db.execute(
                insert(t.audit).values(
                    session_id=record.session_id,
                    student_id=record.student_id,
                    actor_id=actor,
                    changed_at=now,
                    previous=json.dumps(asdict(previous)),
                    current=json.dumps(asdict(record)),
                )
            )
