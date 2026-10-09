"""Micro-benchmarks — regression guards for hot paths.

Run them with `make bench`. In the normal suite they execute once, untimed
(`--benchmark-disable` in pyproject.toml), so the code cannot rot while adding
no timing noise to CI.

**Be clear about what this tier is for.** A micro-benchmark answers "did this
function get dramatically slower?" It does not tell you whether the app is fast
enough — that needs a load test against the real stack — and it will not tell
you *why* something is slow, which needs a profiler. docs/performance.md covers
which of the three to reach for.

Benchmark things that scale with input size and sit on a request path. Do not
benchmark everything: each one can fail for reasons unrelated to your change,
and a suite full of noisy benchmarks is a suite everyone learns to ignore.

The tests are synchronous even though the code under test is async: the
`benchmark` fixture is sync, so the coroutine is driven with `asyncio.run`
inside the timed callable rather than awaited around it.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from attendance.adapters.repositories.fakes import FakeNoteRepository
from attendance.adapters.unit_of_work_fake import FakeUnitOfWork
from attendance.domain.note import Note
from attendance.services.notes import NoteService

pytestmark = pytest.mark.benchmark

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LARGE = 5_000


def test_note_creation_throughput(benchmark):
    """The domain constructor sits on every write path, so it must stay trivial.
    A regression here means something expensive — a network call, a heavy import,
    a regex compiled per call — has crept into what should be a plain object."""
    note = benchmark(Note.create, title="Groceries", body="milk", now=NOW)

    assert note.title == "Groceries"


def test_listing_many_notes_stays_linear(benchmark):
    """Guards against an accidental O(n^2) in the list path.

    The usual regression is a lookup or filter written *inside* the loop over
    results: imperceptible against the 3 rows in a unit test, quadratic against
    the 10,000 a real account has. Sorting keeps this O(n log n); anything much
    worse shows up here as a step change rather than a drift nobody notices.
    """
    repo = FakeNoteRepository()

    async def seed() -> None:
        for index in range(LARGE):
            await repo.add(Note.create(title=f"Note {index}", body="", now=NOW))

    asyncio.run(seed())

    uow = FakeUnitOfWork()
    uow.notes = repo
    service = NoteService(uow)

    notes = benchmark(lambda: asyncio.run(service.list()))

    # Assert the benchmark measured the real thing. A benchmark timing the wrong
    # work is worse than none, because it looks like evidence.
    assert len(notes) == LARGE
