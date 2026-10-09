# Working in this repo

Layered FastAPI backend + React SPA served by that same FastAPI process.
Full explanations in [docs/architecture.md](docs/architecture.md); this file is
the operational summary.

## Commands

```bash
make dev        # dev stack — Vite :5173, API :8000, docs :8000/docs, debugpy :5678
make check      # lint + typecheck + dependency rule + file length + all tests
make sizes      # largest files by code line count
make bench      # timed micro-benchmarks
make format     # auto-fix
make migration m="what changed"   # then READ the generated file
```

Run `make check` before you finish. Use **`/review`** to review a diff against
the guidelines before pushing.

Backend commands run from `backend/` with `uv run ...`; frontend from
`frontend/` with `npm run ...`.

## The rule that matters

**Dependencies point inward.** Each layer may only import from those to its right:

```
entrypoints  ->  services  ->  ports  ->  domain
adapters     ->  ports, domain, config
bootstrap    ->  everything (the composition root)
```

`services` importing `adapters` is a build failure, not a style nit —
`scripts/check_dependency_rule.py` runs in `make lint` and in CI. If a service
needs something external, it needs a **port**.

## Where code goes

| Writing… | Put it in | Not in |
|---|---|---|
| a business rule | `domain/<entity>.py`, as a method on the entity | a service `if` |
| a use case | `services/<thing>.py` — `load → delegate → save` | a route |
| SQL | `adapters/repositories/` | a service |
| an external system call | a port + an adapter | anywhere directly |
| HTTP shaping | `entrypoints/api/routes/` + `schemas/` | a service |
| adapter selection | `bootstrap.py` | anywhere else |

## Guidelines

[docs/backend.md](docs/backend.md) and [docs/frontend.md](docs/frontend.md) are
the normative checklists — read the one you're touching. The highlights are
below; those files have the rest.

**File length: 150 code lines is the guideline, 250 the hard CI limit.** Comments
and docstrings don't count, so explaining yourself is free. `make sizes` shows
the worst offenders. A genuine exception opts out with a comment reading
`file-length-exempt: <reason>`.

## Non-negotiables

- **`domain/` imports nothing external.** No SQLAlchemy, no Pydantic, no FastAPI,
  no SDKs. Entities are plain dataclasses; `adapters/orm/tables.py` maps tables
  onto them.
- **Time is passed into the domain**, never read inside it. Services own the clock.
- **Every port gets a fake** next to its real adapter, and the fake obeys the same
  contract (ordering, `None` semantics).
- **Commit explicitly.** `await uow.commit()` at the end of a write use case.
- **Never catch domain errors in a route.** `exception_handlers.py` maps
  `NotFoundError`/`ConflictError`/`ValidationError` to 404/409/422 once, globally.
  New domain errors subclass one of those three.
- **Use `UtcDatetime`** (`schemas/common.py`) for every datetime on the wire.
  Plain `datetime` serialises inconsistently between SQLite and Postgres.
- **Register nothing after `mount_spa`** in `main.py` — the SPA catch-all matches
  everything, so later routes are unreachable.
- **Frontend: server data lives in TanStack Query, tab-local state in Zustand.**
  Never copy one into the other.
- **`lib/api.ts` is the only place that calls `fetch`.** Paths are always relative.

## Tests

Four tiers — `tests/unit` (domain rules, no I/O), `tests/service`
(`FakeUnitOfWork`), `tests/integration` (real SQL), `tests/e2e` (HTTP). Test each
rule **once**, at the cheapest tier that can see it. Assert on resulting state,
not on which methods were called. Details in [docs/testing.md](docs/testing.md).

Frontend tests query by role and label, and stub `fetch` rather than the hooks.

## Database

Postgres is the **default, not a requirement**. SQLite is a one-line change to
`ATTENDANCE_DATABASE_URL` (the whole test suite runs on it). An app with no state at
all deletes the persistence layers — see [docs/database.md](docs/database.md)
for the checklist. The step people miss: remove the `database` entry from
`READINESS_CHECKS` in `routes/health.py`, or `/health/ready` never passes and the
container is held out of the load balancer forever.

`/health` must never touch a dependency. `tests/e2e/test_no_database.py` enforces
that — don't make it pass by weakening the test.

## Adding a feature

Follow [docs/adding-a-feature.md](docs/adding-a-feature.md) — it lists the exact
files in order, domain first. A new repository means touching three Unit of Work
files (port, real, fake); missing the fake is the usual slip.

## Sign-in

`routes/auth.py` holds the Google/dev sign-in flow and `current_user`. The
notes and files routers are gated in `router.py`; gate new routers the same
way. A route that needs the user takes `user: User = Depends(current_user)`.
E2E tests use `client` (signed in) or `anonymous`.

## The example code

The **Notes** feature and the **files** upload exist to be copied and then
deleted — they are the executable spec for the architecture. The deletion command
list is at the bottom of `docs/adding-a-feature.md`. Don't build new features
inside them; build alongside, then remove them.

## Placeholder naming

Before `make init NAME=...` has been run, the package is `attendance` and env vars are
prefixed `ATTENDANCE_`. In a renamed app, substitute accordingly.
