# Debugging

The dev stack ships with a debugger attached and ports open. Nothing here needs
setting up — it is wired in `make dev`.

## Ports

| Port | What | Override |
|---|---|---|
| 5173 | Vite dev server (the app) | `ATTENDANCE_WEB_HOST_PORT` |
| 8000 | FastAPI — API, `/docs` | `ATTENDANCE_API_HOST_PORT` |
| 5678 | **debugpy** — attach a debugger | `ATTENDANCE_DEBUG_HOST_PORT` |
| 55432 | Postgres, for a GUI client | `ATTENDANCE_DB_HOST_PORT` |
| 4566 | LocalStack (`make up-aws`) | `ATTENDANCE_LOCALSTACK_HOST_PORT` |

Every host port is configurable because running two of these apps at once is
normal and the defaults collide. Only the host side moves; nothing inside the
stack changes. Set them in `.env`.

---

## Backend: attach a debugger

`make dev` runs the API under debugpy on port 5678, in `--listen` mode — it does
**not** wait for a client, so the app boots normally and you can attach at any
time, including after something has already gone wrong.

**VS Code / Cursor:** `.vscode/launch.json` is committed. Pick *Attach to backend
(docker dev)* and set breakpoints. Real breakpoints, full stack, variable
inspection, expression evaluation.

**JetBrains:** a "Python Debug Server" run configuration on port 5678, with the
path mapping `backend` → `/app`.

**If breakpoints show as unbound (a hollow circle), it is the path mapping.** The
editor has the file at a host path, the process reports `/app/...`, and nothing
lines up. That mapping is the one setting people get wrong.

You can also drop `breakpoint()` into the code — it will stop in the attached
session.

### Debugging tests

Use *Debug the backend test under the cursor*. It passes `--no-cov` deliberately:
coverage tracing and the debugger fight over the same `sys.settrace` hook, and
breakpoints get skipped. That is a genuinely baffling ten minutes if you don't
know it.

### Reading the logs

Logs are structured. Locally they are human-readable; in a deployment they are
one JSON object per line.

Every request gets an `X-Request-Id` (echoed as a response header), and every log
line emitted while handling it carries the same `request_id` — including lines
from deep inside a service that knows nothing about HTTP. So a user reporting
"it broke" only needs to give you that header value:

```bash
make logs | grep <request-id>
docker compose -f docker-compose.dev.yml logs backend | jq 'select(.request_id=="...")'
```

Turn up the detail with `ATTENDANCE_LOG_LEVEL=DEBUG`, and see every SQL statement with
`ATTENDANCE_DB_ECHO=true` — the fastest way to spot an N+1 (see
[performance.md](performance.md)).

---

## Frontend

**React Query Devtools** is mounted in dev — the icon in the corner. It lists
every query with its key, state (fresh / stale / fetching) and cached data.

When a screen shows stale, missing or duplicated data, open this *first*. It
usually answers the question outright: the key changed, the query is disabled, or
an invalidation never fired. It is stripped from production builds.

**Breakpoints in .tsx:** use *Debug the frontend in Chrome* from `launch.json`,
or just open DevTools — Vite serves sourcemaps in dev, so you are stepping
through your own TypeScript, not bundled output.

**Full stack in one go:** the *Full stack (backend + Chrome)* compound launches
both, so you can step from a React event handler through the HTTP call into the
service that handles it.

---

## Common situations

**"The API returns 404 but the route exists."** Almost always the SPA catch-all:
anything registered after `mount_spa` in `main.py` is unreachable, because the
catch-all matches every path.

**"My change didn't take effect."** Backend source is bind-mounted and uvicorn
reloads; if it didn't, you probably edited inside the container rather than on
the host. Dependency changes need a rebuild (`make dev` rebuilds).

**"Breakpoints do nothing."** Path mapping (above), or you are debugging tests
with coverage on.

**"It works in dev but not in the built image."** Run `make up` — that is the
only configuration where FastAPI serves the SPA. Dev serves it from Vite, so
static-file and routing problems only appear in the production shape.

**"Postgres connection refused."** The app starts faster than the database.
Compose has a healthcheck and `depends_on: service_healthy`, so this should not
happen — if it does, check the db container's logs rather than the app's.

**"Tests pass alone but fail in the suite."** Shared state leaking between
tests. Backend: settings and the engine are reset by an autouse fixture. Frontend:
every Zustand store must be reset in `src/test/setup.ts`.
