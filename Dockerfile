# syntax=docker/dockerfile:1
#
# Production image: build the SPA, then serve it *and* the API from one FastAPI
# process. One image, one container, one origin — no nginx, no CORS, no separate
# static host, and a deep link like /files works on refresh because FastAPI's
# catch-all returns index.html.
#
# Build context is the repo root, so both frontend/ and backend/ are visible:
#     docker build -t attendance .
#
# The dev image is backend/Dockerfile + frontend/Dockerfile via
# docker-compose.dev.yml; this file is only for shipping.

# ── stage 1: build the SPA ───────────────────────────────────────────────────
FROM node:24-slim AS frontend
WORKDIR /fe
# package files first, so `npm ci` is cached and only re-runs when deps change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /fe/dist

# ── stage 2: python dependencies ─────────────────────────────────────────────
FROM python:3.13-slim AS backend-deps
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
# --no-install-project: dependencies only, so this layer is cached across every
# source change. --frozen: fail if uv.lock is stale rather than silently
# resolving something different from what was tested.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ── stage 3: runtime ─────────────────────────────────────────────────────────
FROM python:3.13-slim AS prod
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    ATTENDANCE_ENVIRONMENT=prod \
    ATTENDANCE_LOG_JSON=true \
    ATTENDANCE_FRONTEND_DIR=/app/frontend

WORKDIR /app
COPY --from=backend-deps /opt/venv /opt/venv
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# The built SPA, served by FastAPI (see entrypoints/api/spa.py).
COPY --from=frontend /fe/dist /app/frontend

# Run as a non-root user. A container escape then lands on an unprivileged
# account instead of root on the host kernel.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2.5)"

# Migrations run at startup, before the server binds. Fine for a single-container
# deploy; if you scale to N replicas, move `alembic upgrade head` into a
# pre-deploy job so N containers don't race to migrate the same database.
#
# No database in this app? Drop the database wait and migration commands here and the two
# alembic COPY lines above — the migration step fails the container on boot when
# there is nothing to migrate. Full checklist in docs/database.md.
CMD ["sh", "-c", "python -m attendance.wait_for_database && alembic upgrade head && exec uvicorn attendance.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --no-access-log"]
