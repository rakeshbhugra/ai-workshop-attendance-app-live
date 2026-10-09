# Attendance project docs

## Product and design

- [Workshop attendance PRD](workshop-attendance-prd.html): product requirements in the OLED document format.
- [Current Schoolnet mock](../mock-ui/index.html): sidebar, workshop list, details panel, and working fictional data.
- [Google sign-in setup](google-auth-setup.md): credentials to add when ready; local development login works without them.
- [Earlier UI ideas](ui-ideas/index.html): reference layouts copied with the starter.

## Application

The starter was copied from the neighboring `ai-workshop-attendance-app` project, initialized from [fastapi-vite-startecode-template](https://github.com/rakeshbhugra/fastapi-vite-startecode-template).

- Frontend: React + TypeScript + Vite. Zustand owns UI state; TanStack Query owns API reads and mutations. Network calls go through `frontend/src/lib/api.ts`.
- Backend: FastAPI + SQLAlchemy + Alembic. PostgreSQL is the runtime database; SQLite is used by fast isolated tests.
- Attendance APIs live under `/api/v1` and require staff authentication. Local development sign-in is explicitly enabled; staging and production reject it.
- Local app ports: frontend 5184, backend 8001, PostgreSQL 55433. See [root setup instructions](../README.md).
- The `live` frontend mode uses backend APIs. Explicit `mock` mode uses a fictional browser dataset without credentials.
- Production serves the built frontend and API from the same FastAPI origin.

Read [architecture](architecture.md), [adding a feature](adding-a-feature.md), [backend guidelines](backend.md), [frontend guidelines](frontend.md), and [testing](testing.md) before extending the application.
