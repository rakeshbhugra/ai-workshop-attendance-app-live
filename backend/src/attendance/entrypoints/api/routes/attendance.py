"""Staff-only workshop administration and session attendance endpoints."""

from fastapi import APIRouter, Depends

from attendance.bootstrap import get_attendance_service
from attendance.domain.user import User
from attendance.entrypoints.api.routes.auth import current_user
from attendance.entrypoints.api.schemas.attendance import (
    AttendanceIn,
    EnrollmentIn,
    RecordIn,
    SessionIn,
    StudentIn,
    StudentOut,
    StudentPatch,
    WorkshopIn,
    WorkshopOut,
)
from attendance.services.attendance import AttendanceService

router = APIRouter(tags=["attendance"])


@router.get("/workshops")
async def workshops(
    service: AttendanceService = Depends(get_attendance_service),
) -> list[WorkshopOut]:
    return [WorkshopOut.of(w, ids) for w, ids in await service.workshops()]


@router.post("/workshops", status_code=201)
async def create_workshop(
    body: WorkshopIn, service: AttendanceService = Depends(get_attendance_service)
) -> WorkshopOut:
    w = await service.create_workshop(body.domain(), body.studentIds)
    return WorkshopOut.of(w, sorted(body.studentIds))


@router.put("/workshops/{workshop_id}/students")
async def enroll(
    workshop_id: str,
    body: EnrollmentIn,
    service: AttendanceService = Depends(get_attendance_service),
) -> EnrollmentIn:
    return EnrollmentIn(studentIds=await service.enroll(workshop_id, body.studentIds))


@router.get("/students")
async def students(
    workshopId: str | None = None, service: AttendanceService = Depends(get_attendance_service)
) -> list[StudentOut]:
    return [StudentOut.of(s) for s in await service.students(workshopId)]


@router.post("/students", status_code=201)
async def create_student(
    body: StudentIn, service: AttendanceService = Depends(get_attendance_service)
) -> StudentOut:
    return StudentOut.of(
        await service.create_student(body.name, body.email, body.college, body.id, body.workshopId)
    )


@router.patch("/students/{student_id}")
async def update_student(
    student_id: str,
    body: StudentPatch,
    service: AttendanceService = Depends(get_attendance_service),
) -> StudentOut:
    return StudentOut.of(
        await service.update_student(student_id, body.model_dump(exclude_unset=True))
    )


@router.get("/sessions")
async def sessions(
    workshopId: str | None = None, service: AttendanceService = Depends(get_attendance_service)
) -> list[SessionIn]:
    return [SessionIn.of(s) for s in await service.sessions(workshopId)]


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionIn, service: AttendanceService = Depends(get_attendance_service)
) -> SessionIn:
    return SessionIn.of(await service.create_session(body.domain()))


@router.get("/sessions/{session_id}/attendance")
async def records(
    session_id: str, service: AttendanceService = Depends(get_attendance_service)
) -> list[RecordIn]:
    return [RecordIn.of(r) for r in await service.records(session_id)]


@router.patch("/sessions/{session_id}/attendance")
async def mark(
    session_id: str,
    body: AttendanceIn,
    user: User = Depends(current_user),
    service: AttendanceService = Depends(get_attendance_service),
) -> list[RecordIn]:
    records = [r.domain(session_id) for r in body.records]
    return [RecordIn.of(r) for r in await service.mark(session_id, records, user.id)]
