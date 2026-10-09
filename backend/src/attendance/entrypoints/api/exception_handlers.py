"""Domain errors → HTTP status codes, in exactly one place.

The domain raises ``NoteNotFound``; it has never heard of 404. This module is the
translation layer, and it is registered once at app creation. The payoff: a new
domain error added six months from now gets the right status code automatically,
as long as it subclasses one of the three bases in ``domain/exceptions.py``.

Order matters — handlers are matched most-specific-first, so the base
``DomainError`` handler at the end only catches subclasses nothing else claimed.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from attendance.config.logging import get_logger
from attendance.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)

log = get_logger(__name__)

_STATUS_BY_ERROR: list[tuple[type[DomainError], int]] = [
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    # 422 written literally: Starlette renamed the constant, and the literal
    # works across versions without a deprecation warning either way.
    (ValidationError, 422),
    # Anything else that made it out of the domain is a rule we forgot to
    # classify — 400 rather than a 500, because it *is* the caller's fault.
    (DomainError, status.HTTP_400_BAD_REQUEST),
]


def register_exception_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR:

        async def handler(
            request: Request,
            exc: Exception,
            # Bound as defaults: without this every closure would capture the
            # last loop values and all four handlers would return 400.
            _status: int = status_code,
            _type: type[DomainError] = error_type,
        ) -> JSONResponse:
            log.info(
                "domain_error",
                error=_type.__name__,
                detail=str(exc),
                path=request.url.path,
            )
            # ``detail`` matches FastAPI's own error shape, so the frontend has
            # one error format to handle rather than two.
            return JSONResponse(status_code=_status, content={"detail": str(exc)})

        app.add_exception_handler(error_type, handler)
