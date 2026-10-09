"""The versioned API router — one place that knows every route module.

Versioning from day one (``/api/v1``) costs nothing now and is very awkward to
retrofit once a mobile client is pinned to your unversioned URLs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from attendance.entrypoints.api.routes import attendance, auth, files, notes

api_router = APIRouter()
api_router.include_router(auth.router)
# Everything else needs a signed-in user. A route that needs *who* reads
# `user: User = Depends(auth.current_user)` itself; FastAPI resolves it once.
signed_in = [Depends(auth.current_user)]
api_router.include_router(attendance.router, dependencies=signed_in)
api_router.include_router(notes.router, dependencies=signed_in)
api_router.include_router(files.router, dependencies=signed_in)
