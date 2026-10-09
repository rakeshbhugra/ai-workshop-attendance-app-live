"""Alembic environment — async engine, URL and metadata taken from the app.

Two things worth knowing:

* The URL comes from ``Settings``, never from alembic.ini. One source of truth
  means ``alembic upgrade head`` can't migrate a different database than the one
  the app is about to use.
* ``target_metadata`` is the same metadata object the imperative mappings are
  built on, and importing ``attendance.adapters.orm`` is what registers every table
  on it. Forget that import and autogenerate cheerfully writes a migration that
  drops all your tables.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from attendance.adapters.orm import metadata
from attendance.config.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = metadata


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Detect column type changes, not just added/dropped columns — the
        # default misses a String(50) → String(200) widening entirely.
        compare_type=True,
        compare_server_default=True,
        # Batch mode makes ALTER TABLE work on SQLite, which otherwise can't
        # alter columns at all. A no-op on Postgres.
        render_as_batch=connection.dialect.name == "sqlite",
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (``alembic upgrade head --sql``),
    for handing a change to a DBA or reviewing it before a production run."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # a migration run is short-lived; no pool needed
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
