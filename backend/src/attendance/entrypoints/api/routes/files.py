"""HTTP entrypoint for file upload/download.

Backed by the ObjectStorage port, so these endpoints work identically against
in-memory storage (default), LocalStack (``make up-aws``) and real S3 (set
``ATTENDANCE_S3_BUCKET`` and give the task an IAM role).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from attendance.bootstrap import get_file_service
from attendance.services.files import FileService

router = APIRouter(prefix="/files", tags=["files"])

# Reject oversized uploads before they reach storage. FastAPI buffers to a temp
# file past ~1MB, so this guards the storage bill, not the process memory.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    service: FileService = Depends(get_file_service),
) -> dict[str, str]:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        # A size cap is a transport concern, not a business rule, so it is
        # enforced here rather than in the service.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Files must be {MAX_UPLOAD_BYTES // (1024 * 1024)}MB or smaller.",
        )
    key = await service.store(
        filename=file.filename or "file",
        data=data,
        content_type=file.content_type or "",
    )
    return {"key": key}


# ``:path`` because a key contains slashes (uploads/<uuid>/<filename>).
@router.get("/{key:path}")
async def download_file(
    key: str,
    service: FileService = Depends(get_file_service),
) -> Response:
    stored = await service.fetch(key)
    filename = key.rsplit("/", 1)[-1]
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        # ``inline`` lets the browser preview images/PDFs; the filename is still
        # offered for a manual save.
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
