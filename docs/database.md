# Choosing a database (or none)

Postgres is the **default**, not a requirement. Three tiers, in rising order of
how much you have to change.

| Tier | Change needed | Use when |
|---|---|---|
| **Postgres** | nothing — it's the default | concurrent writers, more than one instance, anything that outlives a container |
| **SQLite** | one environment variable | single instance, low write volume, an internal tool, a prototype |
| **No database** | delete the persistence layers (below) | the app owns no state — an LLM wrapper, a proxy, a dashboard over someone else's API |

Pick the smallest one that fits. A Postgres container for an app that stores
nothing is a thing to run, patch, back up and pay for, forever.

---

## Tier 2 — SQLite

```bash
ATTENDANCE_DATABASE_URL=sqlite+aiosqlite:///./local.db
```

That is the whole change. Everything else — Alembic, the repositories, the Unit
of Work, the domain — is dialect-agnostic and works unmodified. Then delete the
`db` service from whichever compose file you use, and its `depends_on`.

**How we're sure it works:** the entire backend test suite already runs on
SQLite, in memory, on every CI run. If CI is green, SQLite works.

Know what you're accepting: one writer at a time, no concurrent write scaling,
and the file lives in the container — so **it is destroyed on every deploy
unless you mount a volume.** SQLite also ignores `DateTime(timezone=True)` and
returns naive datetimes, which is why every datetime on the wire goes through
`UtcDatetime` (`schemas/common.py`).

## Tier 3 — no database at all

### First, the trap

`/health/ready` checks every entry in `READINESS_CHECKS`
(`entrypoints/api/routes/health.py`). Leave the database entry in an app that
has no database and the probe **never passes**, so the orchestrator holds the
container out of the load balancer forever. It presents as a broken deploy, not
as a configuration mistake, and it costs an afternoon.

Deleting that one line is the single most important step below. An empty
`READINESS_CHECKS` means "always ready", which is correct for an app with no
external dependencies.

### The removal

```bash
# 1. persistence layers
git rm -r backend/src/attendance/adapters/orm \
          backend/src/attendance/adapters/repositories \
          backend/alembic backend/alembic.ini
git rm backend/src/attendance/adapters/unit_of_work.py \
       backend/src/attendance/adapters/unit_of_work_fake.py \
       backend/src/attendance/ports/repositories.py \
       backend/src/attendance/ports/unit_of_work.py \
       backend/src/attendance/config/database.py

# 2. the example feature, which is entirely database-backed
#    (see the deletion list in adding-a-feature.md)
```

Then, by hand:

- [ ] **`routes/health.py`** — delete the `("database", _check_database)` entry,
      `_check_database`, and the now-unused imports. **The trap above.**
- [ ] **`main.py`** — drop `start_mappers()`, `dispose_engine()`/`reset_engine()`
      and their imports.
- [ ] **`bootstrap.py`** — drop `get_unit_of_work` and any service taking a UoW.
- [ ] **`config/settings.py`** — drop `database_url` and `db_echo`.
- [ ] **`pyproject.toml`** — drop `sqlalchemy`, `alembic`, `asyncpg`, `aiosqlite`,
      `greenlet`. Then `uv lock`.
- [ ] **compose files** — drop the `db` service, its volume, and both
      `depends_on` blocks.
- [ ] **`Dockerfile`** — drop `alembic upgrade head &&` from the `CMD`, and the
      `COPY backend/alembic` lines. Leaving the migration step in an app with no
      migrations fails the container on boot.
- [ ] **`tests/conftest.py`** — drop `session_factory`, `session`, `uow` and the
      `get_db` override.
- [ ] **`scripts/check_dependency_rule.py`** — nothing to change; it works on
      whatever layers remain.

Keep `tests/e2e/test_no_database.py`. It is what proves the app still boots and
reports itself alive with no database anywhere, and it keeps that true as the
app grows.

### What you keep

Everything that makes the architecture worth having. Domain entities and their
rules, services, ports and adapters, the dependency rule, the four test tiers.
A repository is just *one kind of adapter* — dropping it changes nothing about
how you talk to an LLM, an object store or an auth provider (see
[blocks.md](blocks.md)).

Services still take ports; they just take the ports they actually need:

```python
class SummaryService:
    def __init__(self, completer: Completer) -> None:   # no UoW anywhere
        self._completer = completer
```

---

## Adding a database later

Nothing above is one-way. If a no-database app grows state, re-add the layers in
the order in [adding-a-feature.md](adding-a-feature.md) — domain first. Because
the services were already written against ports, they mostly gain a `uow`
argument rather than being rewritten.

Going from SQLite to Postgres is a URL change plus a data migration. Do it before
you need a second instance, not after.
