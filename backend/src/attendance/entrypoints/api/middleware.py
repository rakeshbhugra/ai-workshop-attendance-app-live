"""Request-scoped logging context.

Binds a request id into structlog's contextvars so *every* log line emitted
while handling a request carries it — including lines from a service three layers
down that knows nothing about HTTP. Then echoes it back as ``X-Request-Id`` so a
user reporting "it broke" can hand you the exact id to grep for.

Written as pure ASGI-adjacent middleware over ``BaseHTTPMiddleware``'s dispatch
hook, which is enough here; drop to raw ASGI only if you ever need to touch
streaming response bodies.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from attendance.config.logging import get_logger
from attendance.config.settings import get_settings

log = get_logger("http")

REQUEST_ID_HEADER = "X-Request-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Cookies are ambient credentials. Reject browser writes from a different origin.
        origin = request.headers.get("origin")
        settings = get_settings()
        allowed = {str(request.base_url).rstrip("/"), *settings.cors_origins}
        if settings.public_url:
            allowed.add(settings.public_url.rstrip("/"))
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin is not None
            and origin.rstrip("/") not in allowed
        ):
            return JSONResponse({"detail": "Cross-origin write rejected"}, status_code=403)
        # Honour an upstream id when there is one (load balancer, calling
        # service) so a single trace survives across service boundaries.
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Log with the bound context before the exception escapes, otherwise
            # the 500 shows up in logs with no request id attached to it.
            log.exception("request_failed", duration_ms=_elapsed_ms(started))
            raise
        log.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=_elapsed_ms(started),
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
