"""Shared fixtures.

The layering pays off here. Most tests need *no* fixtures at all (domain tests
construct entities directly), service tests need one cheap object
(``FakeUnitOfWork``), and only the integration/e2e tests below need a database —
which is why they are the small top of the pyramid instead of all of it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from attendance.adapters.orm import metadata, start_mappers
from attendance.adapters.storage.in_memory import InMemoryObjectStorage
from attendance.adapters.unit_of_work_fake import FakeUnitOfWork
from attendance.bootstrap import get_object_storage
from attendance.config.database import get_db, reset_engine
from attendance.config.settings import Settings, set_settings
from attendance.main import create_app


@pytest.fixture(autouse=True)
def _isolate_settings() -> Iterator[None]:
    """Undo process-wide state after every test.

    ``create_app(settings)`` installs its settings for the whole process (see
    config/settings.py). Without this, a test that points the app at an
    unreachable database leaves that URL in place for whatever runs next — a
    failure that depends on test *order*, which is the worst kind to debug.
    """
    yield
    set_settings(Settings())
    reset_engine()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    """The service-test workhorse: a real, working UoW with dicts instead of a
    database. Fast enough that service tests stay in the 'run on every save' tier."""
    return FakeUnitOfWork()


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A schema-fresh in-memory SQLite database per test.

    StaticPool + a single connection is what keeps ``:memory:`` alive across the
    session objects in one test — the default pool would hand out a new
    connection and therefore a new, empty database.

    SQLite is not Postgres, so this cannot catch dialect-specific bugs (JSONB
    operators, ``ON CONFLICT`` variants, timezone handling). Run the suite
    against Postgres in CI as well — see `make test-pg`.
    """
    start_mappers()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        # create_all, not Alembic: tests want the *current* mapping, and running
        # the full migration history per test would be slow and would break the
        # moment an old migration references a since-deleted table.
        await conn.run_sync(metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def anonymous(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """The whole app over ASGI — no network, no port, no running server.

    Dependency overrides are the seam: the app is built exactly as production
    builds it, then the two things that touch the outside world (database,
    object storage) are swapped for test doubles.
    """
    app = create_app(
        Settings(environment="test", log_level="WARNING", cors_origins=[], public_url="")
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    # One instance for the whole test, not one per request — otherwise an upload
    # and the download that follows it would talk to two different stores.
    storage = InMemoryObjectStorage()
    app.dependency_overrides[get_object_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client(anonymous: AsyncClient) -> AsyncClient:
    """``anonymous``, signed in as the dev user. Most e2e tests want this."""
    login = await anonymous.get("/api/v1/auth/dev/login")
    await anonymous.get(login.headers["location"])
    return anonymous
