# Schoolnet workshop attendance app

React + TypeScript + Vite frontend, Zustand for UI state, TanStack Query for API data, and a FastAPI backend backed by PostgreSQL. The Schoolnet interface follows the sidebar, workshop list, and details-panel layout from `mock-ui/`.

Starter source copied from the neighboring `ai-workshop-attendance-app` project, which was initialized from [fastapi-vite-startecode-template](https://github.com/rakeshbhugra/fastapi-vite-startecode-template). Existing mock UI and PRD are preserved.

## Local development

Prerequisites: Docker, Node.js 22+, npm, Python 3.13, and uv.

```sh
make install
cp .env.example backend/.env
make db-up
make db-migrate
make seed
```

Create `frontend/.env.local` with:

```dotenv
VITE_ATTENDANCE_DATA_MODE=live
VITE_API_PROXY=http://localhost:8001
```

Run in separate terminals:

```sh
make dev-api
make dev-web
```

App: http://localhost:5184. API docs: http://localhost:8001/docs. PostgreSQL: `localhost:55433`, development database/user/password: `attendance`.

Use the **development login** on the sign-in page. This explicitly enabled local bypass uses real database-backed APIs without Google secrets. It is disabled in staging and production.

The Docker project is `attendance-live`, with its own PostgreSQL volume and ports so it can coexist with the neighboring starter. To run the whole Docker stack, use `make dev`; it serves the same frontend at port 5184.

## Frontend modes

- `live` (default): authenticated API reads and mutations backed by PostgreSQL.
- `mock`: explicitly selected fictional browser data for UI review, without backend/auth. This mode does not silently replace failed live requests.

The database seed comes from `mock-ui/mock-data.json`. Seeding is for local development, not an automatic production operation.

## Google sign-in later

See [Google auth setup](docs/google-auth-setup.md). Add credentials to the ignored environment file, then restart the backend. Do not put client secrets in `VITE_` variables.

## Verification

```sh
make check
cd frontend && npm run build
```

Backend follows the starter's domain, ports, services, adapters, and HTTP layers. API routes are under `/api/v1`. See [architecture](docs/architecture.md), [frontend guidelines](docs/frontend.md), and [backend guidelines](docs/backend.md).
