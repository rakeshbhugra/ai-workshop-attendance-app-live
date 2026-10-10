"""Startup must gate migrations even when Compose isn't managing the database."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from attendance import wait_for_database as startup
from attendance.config.settings import Settings, set_settings


async def test_startup_retries_until_database_recovers(monkeypatch):
    set_settings(Settings(db_startup_retry_seconds=0.001))
    probe = AsyncMock(side_effect=[ConnectionError(), TimeoutError(), None])
    dispose = AsyncMock()
    monkeypatch.setattr(startup, "check_database", probe)
    monkeypatch.setattr(startup, "dispose_engine", dispose)

    await startup.wait_for_database()

    assert probe.await_count == 3
    dispose.assert_awaited_once()


@pytest.mark.parametrize("hung", [False, True])
async def test_startup_has_a_total_deadline(monkeypatch, hung):
    set_settings(Settings(db_startup_timeout_seconds=0.02, db_startup_retry_seconds=0.001))

    async def unavailable():
        if hung:
            await asyncio.sleep(10)
        raise ConnectionError("database unavailable")

    dispose = AsyncMock()
    monkeypatch.setattr(startup, "check_database", unavailable)
    monkeypatch.setattr(startup, "dispose_engine", dispose)

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(startup.wait_for_database(), timeout=1)
    dispose.assert_awaited_once()


def test_startup_command_exits_unsuccessfully_after_timeout(monkeypatch):
    monkeypatch.setattr(startup, "wait_for_database", AsyncMock(side_effect=TimeoutError()))
    with pytest.raises(SystemExit) as failure:
        startup.main()
    assert failure.value.code == 1
