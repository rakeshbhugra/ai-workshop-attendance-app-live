"""Async engine, session factory, and the per-request session dependency.

Everything is built on first use, not at import time. That matters more than it
looks: importing this module must never open a connection, or an unlucky test —
or Alembic, or a management script — would quietly reach for a database that
isn't there.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from attendance.config.settings import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _connect_args(url: str) -> dict[str, Any]:
    """asyncpg rejects libpq's ``?sslmode=`` query parameter, so TLS is negotiated
    here instead. 'prefer' encrypts against a managed Postgres that requires it
    (RDS with rds.force_ssl=1) and still connects to a plain compose Postgres.
    SQLite takes no ssl argument at all."""
    return {"ssl": "prefer"} if url.startswith("postgresql") else {}


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            # Managed Postgres drops idle connections and fails over without
            # warning; re-check the connection before handing it out.
            pool_pre_ping=True,
            connect_args=_connect_args(settings.database_url),
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            # Domain objects stay usable after commit. Without this, reading
            # note.title after the UoW commits triggers a lazy refresh — which
            # raises in async code, and is the single most common surprise here.
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one session per request, closed when it ends."""
    async with get_sessionmaker()() as session:
        yield session


def reset_engine() -> None:
    """Drop the cached engine so the next call rebuilds it from current settings.

    Synchronous and deliberately not disposing: it runs at app construction,
    before any connection has been opened. Use ``dispose_engine`` at shutdown,
    when there is a live pool to close.
    """
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


async def dispose_engine() -> None:
    """Close the pool on shutdown so connections don't linger."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
