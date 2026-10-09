"""Portable SQL tables. Constraints are mirrored by the migration."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    Uuid,
)

from attendance.adapters.orm.registry import metadata

students = Table(
    "students",
    metadata,
    Column("id", String(80), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("email", String(320), nullable=False, unique=True),
    Column("college", String(240), nullable=False),
    Column("active", Boolean, nullable=False),
)
workshops = Table(
    "workshops",
    metadata,
    Column("id", String(80), primary_key=True),
    Column("title", String(200), nullable=False),
    Column("description", Text, nullable=False),
    Column("category", String(200), nullable=False),
    Column("facilitator", String(200), nullable=False),
    Column("email", String(320), nullable=False),
    Column("dates", String(200), nullable=False),
    Column("days", String(200), nullable=False),
    Column("location", String(240), nullable=False),
    Column("active", Boolean, nullable=False),
)
enrollments = Table(
    "enrollments",
    metadata,
    Column("workshop_id", String(80), ForeignKey("workshops.id"), primary_key=True),
    Column("student_id", String(80), ForeignKey("students.id"), primary_key=True),
)
sessions = Table(
    "workshop_sessions",
    metadata,
    Column("id", String(80), primary_key=True),
    Column("workshop_id", String(80), ForeignKey("workshops.id"), nullable=False),
    Column("title", String(200), nullable=False),
    Column("date", String(10), nullable=False),
    Column("start", String(8), nullable=False),
    Column("end", String(8), nullable=False),
    Column("timezone", String(80), nullable=False),
    CheckConstraint('"end" > start', name="ck_session_order"),
    Index("ix_sessions_workshop_date", "workshop_id", "date"),
)
roster = Table(
    "session_roster",
    metadata,
    Column("session_id", String(80), ForeignKey("workshop_sessions.id"), primary_key=True),
    Column("student_id", String(80), ForeignKey("students.id"), primary_key=True),
)
records = Table(
    "attendance_records",
    metadata,
    Column("session_id", String(80), primary_key=True),
    Column("student_id", String(80), primary_key=True),
    Column("status", String(10), nullable=False),
    Column("check_in", String(8), nullable=False),
    Column("check_out", String(8), nullable=False),
    ForeignKeyConstraint(
        ["session_id", "student_id"], ["session_roster.session_id", "session_roster.student_id"]
    ),
    CheckConstraint("status IN ('unmarked','present','absent')", name="ck_attendance_status"),
    CheckConstraint(
        "check_out = '' OR (check_in <> '' AND check_out >= check_in)", name="ck_attendance_times"
    ),
    CheckConstraint(
        "status = 'present' OR (check_in = '' AND check_out = '')",
        name="ck_attendance_present_times",
    ),
)
audit = Table(
    "attendance_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(80), ForeignKey("workshop_sessions.id"), nullable=False),
    Column("student_id", String(80), ForeignKey("students.id"), nullable=False),
    Column("actor_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    Column("previous", Text, nullable=False),
    Column("current", Text, nullable=False),
)
