# syntax=docker/dockerfile:1
#
# Development image for the backend only — hot reload + a debugpy port.
# Production is the root Dockerfile, which bakes the SPA in alongside the API.
FROM python:3.13-slim AS dev
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # The venv lives outside /app so the source bind-mount doesn't shadow it —
    # mount ./backend over /app with the venv inside and the interpreter
    # vanishes the moment the container starts.
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    # Silences debugpy's "frozen modules" warning on every start. The warning is
    # about breakpoints inside the stdlib's own import machinery, which is not
    # something you will ever want to step through.
    PYDEVD_DISABLE_FILE_VALIDATION=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

EXPOSE 8000 5678

# debugpy listens on 5678 without waiting for a client, so the app starts
# normally and you can attach from VS Code / PyCharm whenever you want.
# --timeout-graceful-shutdown stops --reload hanging on an open connection.
CMD ["sh", "-c", "alembic upgrade head && python -m debugpy --listen 0.0.0.0:5678 -m uvicorn attendance.main:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 1"]
