from pathlib import Path

from attendance import seed
from attendance.adapters.repositories.attendance import SqlAttendanceRepository

FIXTURE = Path(__file__).resolve().parents[3] / "mock-ui" / "mock-data.json"


async def test_seed_import_is_idempotent(monkeypatch, session_factory):
    monkeypatch.setattr(seed, "get_sessionmaker", lambda: session_factory)
    await seed.seed(FIXTURE)
    await seed.seed(FIXTURE)
    async with session_factory() as db:
        repo = SqlAttendanceRepository(db)
        assert len(await repo.students()) == 12
        assert len(await repo.workshops()) == 4
        assert len(await repo.sessions()) == 10
        assert (await repo.records("ai-1"))[0].duration_minutes() == 105
