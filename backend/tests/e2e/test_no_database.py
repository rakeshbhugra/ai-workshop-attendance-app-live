"""The liveness path must never touch the database.

Two things depend on this and both are easy to break by accident:

1. **Apps built from this template that have no database at all** (see
   docs/database.md). They delete the persistence layers; whatever is left must
   still boot and report itself alive.
2. **Apps that do have a database, during an outage.** If ``/health`` needs the
   database, a thirty-second blip makes the orchestrator conclude every
   container is dead and restart the entire fleet — turning a brief degradation
   into a full outage exactly when you least want one.

So this file builds the app pointed at a database that cannot exist and asserts
the alive-path still works. It is a regression guard: the moment somebody adds a
query to ``/health``, or imports something DB-backed at module scope, it fails.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from attendance.config import database_readiness
from attendance.config.settings import Settings
from attendance.main import create_app

# Port 1 on loopback: nothing can be listening, so any connection attempt fails
# immediately rather than hanging the test for a connect timeout.
UNREACHABLE_DATABASE = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/nothing"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        cors_origins=[],
        database_url=UNREACHABLE_DATABASE,
    )


async def test_the_app_builds_with_no_reachable_database(settings: Settings):
    """Construction must not connect. If it did, every deployment would depend on
    the database being up *before* the app starts, rather than recovering on its
    own once it comes back."""
    assert create_app(settings) is not None


async def test_liveness_is_ok_while_the_database_is_unreachable(settings: Settings):
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_reports_the_database_as_down_without_raising(settings: Settings):
    """Readiness is allowed to fail — that is its job — but it must answer with a
    503, not blow up with a connection error the orchestrator can't interpret."""
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}


async def test_readiness_is_ready_with_a_reachable_database():
    app = create_app(Settings(environment="test", database_url="sqlite+aiosqlite://"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}
    await database_readiness.get_engine().dispose()


async def test_readiness_times_out_a_stalled_connection(settings, monkeypatch):
    settings.db_probe_timeout_seconds = 0.01

    @asynccontextmanager
    async def stalled_connection():
        await asyncio.sleep(10)
        yield AsyncMock()

    class StalledEngine:
        connect = staticmethod(stalled_connection)

    monkeypatch.setattr(database_readiness, "get_engine", lambda: StalledEngine())
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await asyncio.wait_for(client.get("/health/ready"), timeout=1)
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}
