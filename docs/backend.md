# Backend guidelines

The normative checklist. [architecture.md](architecture.md) explains *why* the
layers exist; this is what to actually do while writing code, and what the review
skill (`/review`) checks against.

---

## Layering

The dependency rule is enforced by `scripts/check_dependency_rule.py` in CI. The
things it cannot catch, which reviewers must:

- **A rule that drifted out of the domain.** `if note.archived_at is not None:
  raise ...` inside a service is a domain rule in the wrong place. It will be
  forgotten by the next caller — a CLI command, a worker, an admin action.
- **An anemic entity.** A dataclass with no methods and a service full of
  procedures is this architecture's folder structure without its benefit.
- **A fat route.** Routes parse, call one service method, and shape the
  response. An `if` in a route is a decision that belongs in a service.
- **A service taking a session or a concrete repository** instead of the
  `UnitOfWork` port. It compiles; it also makes the service untestable without a
  database, so it stops being tested.

## Domain

- Plain dataclasses. No SQLAlchemy, no Pydantic, no FastAPI, no SDKs — enforced.
- A `create()` classmethod validating invariants, so an invalid instance cannot
  exist.
- **Time is a parameter, never read inside.** `datetime.now()` in a domain method
  makes the rule untestable at a specific moment. Services own the clock.
- Errors subclass `NotFoundError` / `ConflictError` / `ValidationError` from
  `domain/exceptions.py`. That is what maps them to 404/409/422, once, globally.
- No `print`, no logging, no I/O.

## Services

- One public method per use case. Shape: `load → delegate to the domain → save`.
- Take **ports**, never adapters or sessions.
- `await uow.commit()` explicitly. Forgetting loses the write, which is the safe
  direction to fail in.
- Turning a repository's `None` into a `NotFoundError` is a use-case decision and
  belongs here, not in the adapter.
- No HTTP vocabulary. A service that raises `HTTPException` cannot be reused by a
  worker or a CLI.

## Repositories and adapters

- Collection vocabulary: `add`, `get`, `list`. One repository per **aggregate
  root**, not per table.
- Every port gets a fake next to the real adapter, and **the fake obeys the same
  contract** — same ordering, same `None` semantics. When they drift, service
  tests pass for the wrong reason.
- Filter and sort in the query, not in Python afterwards. `list()[:10]` after
  fetching 50,000 rows is a query bug wearing a slice.
- Adapters translate vendor errors into domain errors. A `ClientError` should not
  reach a service.

## Async

- **Never call blocking code in an `async def`.** One `requests.get()` or
  `time.sleep()` stalls the entire event loop — every concurrent request, not
  just this one. Ruff's `ASYNC` rules catch the common cases; they do not catch a
  blocking third-party SDK.
- Wrap unavoidably-sync SDKs in `asyncio.to_thread` (see `adapters/storage/s3.py`).
- Use `asyncio.gather` for independent awaits rather than awaiting in sequence.

## Database

- **Every schema change is an Alembic migration**, and you read the generated
  file before committing. Autogenerate misses renames (it writes drop+add, losing
  data) and never writes a backfill.
- **Declare indexes and constraints in `adapters/orm/tables.py`**, not only in
  the migration — Alembic compares against that metadata, so an index that exists
  only in a migration shows up as "removed" and the next autogenerate drops it.
  `alembic check` catches this.
- `DateTime(timezone=True)` for every timestamp, and `UtcDatetime` on the wire.
- **Beware N+1.** A loop that awaits a query per item is the most common
  performance bug in this shape of app. Fetch the set in one query and map it.
  See [performance.md](performance.md).
- Postgres is the default, not a requirement — see [database.md](database.md).

## API layer

- Versioned under `/api/v1`. Health sits outside the prefix.
- Pydantic schemas are the wire shape; map to/from domain explicitly with an
  `of()` classmethod rather than `model_validate`, so a domain rename becomes a
  type error instead of a silently changed API contract.
- **Schema validation vs domain validation:** shape and type (max length,
  required) at the edge; business rules in the domain, so they hold for every
  entrypoint.
- Never catch domain errors in a route.
- Register nothing after `mount_spa` — the catch-all makes it unreachable.

## Errors and logging

- `log = get_logger(__name__)`, structured key-values: `log.info("note_archived",
  note_id=str(note.id))`, not f-strings. The point is being able to query
  `note_id=...` rather than grep a sentence.
- Event names are `snake_case` nouns/verbs, stable over time — they are what you
  build alerts on.
- **Never log secrets, tokens, full request bodies or personal data.** The
  database URL is logged host-only for exactly this reason.
- Catch narrowly. A bare `except Exception` that swallows and continues turns a
  visible failure into corrupt data. Readiness checks are the deliberate
  exception, and they log.

## Configuration

- Everything through `Settings`; no `os.environ` reads scattered around.
- Every setting needs a default that lets a fresh clone run.
- Secrets only from the environment. Nothing real in `.env.example`.

## Files and naming

- **150 code lines guideline, 250 hard limit** — comments and docstrings are
  excluded, so explaining yourself costs nothing. Over 150, split by
  responsibility: a second service, a helper module, a split repository.
- `snake_case` modules; one aggregate per domain module.
- Type hints everywhere — `mypy --strict` is on. Prefer a precise type over
  `Any`; a `# type: ignore` needs a reason next to it.

## Tests

Four tiers, and each rule tested **once at the cheapest tier that can see it**.
Assert on resulting state, not on which methods were called. Full detail in
[testing.md](testing.md).

New code needs: a domain test per rule, a service test per use case, an
integration test if you touched an adapter, and an e2e test only for a new HTTP
contract.
