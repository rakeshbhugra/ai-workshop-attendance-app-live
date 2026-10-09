"""Liveness and readiness.

They answer different questions and orchestrators treat them differently:

* ``/health``  — "is this process alive?" **Must never touch a dependency.** If
  it did, a brief database blip would make the orchestrator kill healthy
  containers and turn a small outage into a large one. Locked in by
  ``tests/e2e/test_no_database.py``.
* ``/health/ready`` — "can this process serve traffic *right now*?" Checks the
  dependencies it genuinely needs, so a container is pulled from the pool while
  one is down and returned when it recovers.

**If your app has no database, delete the database entry from READINESS_CHECKS
below** (see docs/database.md). A readiness probe that checks a dependency you
do not have never passes, so the container is held out of the load balancer
forever — which looks like a broken deploy rather than a configuration choice.
An empty list means "always ready", which is correct for an app with no
external dependencies.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from attendance.config.database import get_engine
from attendance.config.logging import get_logger
from attendance.config.settings import get_settings

router = APIRouter(tags=["meta"])
log = get_logger(__name__)


async def _check_database() -> None:
    """Raises if the database is unreachable."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


# One entry per dependency this process needs before it can serve traffic. Add
# a line when you add a block (cache, queue, auth provider); delete a line when
# you drop one. Keep it to dependencies a request genuinely cannot proceed
# without — checking something optional here converts a degraded feature into a
# total outage.
READINESS_CHECKS: list[tuple[str, Callable[[], Awaitable[None]]]] = [
    ("database", _check_database),
]


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@router.get("/health/ready")
async def ready() -> JSONResponse:
    results: dict[str, str] = {}
    healthy = True

    for name, check in READINESS_CHECKS:
        try:
            await check()
        except Exception as exc:  # noqa: BLE001 - readiness must report, never raise
            log.warning("readiness_check_failed", dependency=name, error=str(exc))
            results[name] = "down"
            healthy = False
        else:
            results[name] = "up"

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if healthy else "unavailable", **results},
    )
