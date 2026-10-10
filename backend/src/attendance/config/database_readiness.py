"""Bounded database probes shared by readiness and container startup."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from attendance.config.database import get_engine
from attendance.config.settings import get_settings


async def check_database() -> None:
    """Check a real query, including connection acquisition, within a deadline."""
    async with asyncio.timeout(get_settings().db_probe_timeout_seconds):
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
