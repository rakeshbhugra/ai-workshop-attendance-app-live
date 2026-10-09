"""FastAPI application factory + local entrypoint.

``create_app()`` is a factory, not a module-level app, so tests can build a fresh
instance with overridden dependencies. The module-level ``app`` at the bottom
exists only because uvicorn needs an import string to point at.

Registration order in ``create_app`` is load-bearing and marked inline. Read it
top to bottom before changing it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from attendance.adapters.orm import start_mappers
from attendance.config.database import dispose_engine, reset_engine
from attendance.config.logging import configure_logging, get_logger
from attendance.config.settings import Settings, get_settings, set_settings
from attendance.entrypoints.api.exception_handlers import register_exception_handlers
from attendance.entrypoints.api.middleware import RequestContextMiddleware
from attendance.entrypoints.api.router import api_router
from attendance.entrypoints.api.routes import health
from attendance.entrypoints.api.spa import mount_spa

API_PREFIX = "/api/v1"

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    log.info(
        "app_starting",
        app=settings.app_name,
        environment=settings.environment,
        database=settings.database_url.split("@")[-1],  # never log credentials
    )
    # Note there is no create_all() here. Schema changes go through Alembic
    # (`make migrate`), so what runs in dev is exactly what runs in production.
    yield
    await dispose_engine()
    log.info("app_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is not None:
        # Install them process-wide, or they would only apply to the lines in
        # this function: everything reaching for get_settings() later (the
        # engine, the readiness check, the storage builder) would still read the
        # environment, and the app would quietly use a different database than
        # the caller asked for. Resetting the engine makes a new database_url
        # actually take effect.
        set_settings(settings)
        reset_engine()
    settings = settings or get_settings()
    if settings.environment in {"staging", "prod"}:
        if settings.auth_dev_login or not settings.cookie_secure:
            raise RuntimeError("Production requires secure cookies and dev login disabled")
        if settings.session_secret == "dev-session-secret":  # noqa: S105
            raise RuntimeError("Production requires a strong session secret")
        if settings.google_client_id and not (
            settings.allowed_staff_emails or settings.allowed_email_domains
        ):
            raise RuntimeError("Google staff access requires an email or domain allowlist")
    configure_logging(level=settings.log_level, json_output=settings.log_json)

    # Map the domain classes onto their tables. Here rather than in the lifespan
    # on purpose: lifespan only runs for a live server, so anything else that
    # builds the app — a TestClient, a management script, a worker importing a
    # service — would otherwise fail deep inside SQLAlchemy with
    # "Column expression ... expected, got <class Note>", which says nothing
    # about the actual cause. Idempotent, so calling it again costs nothing.
    #
    # Non-HTTP entrypoints that never build the app (a standalone CLI, a queue
    # consumer) must call start_mappers() themselves before their first query.
    start_mappers()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs are useful everywhere except a public production
        # deployment, where they hand an attacker a map of the API.
        docs_url="/docs" if settings.environment != "prod" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.environment != "prod" else None,
    )

    # 1. Middleware first — outermost wrapper, so it sees every request including
    #    ones that later blow up in a handler.
    app.add_middleware(RequestContextMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 2. Domain error → status code mapping.
    register_exception_handlers(app)

    # 3. Routes. Health sits outside the version prefix because uptime checks and
    #    orchestrators should never have to care what version the API is on.
    app.include_router(health.router)
    app.include_router(api_router, prefix=API_PREFIX)

    # 4. The SPA catch-all, LAST. It matches every remaining path, so anything
    #    registered after this line is dead code.
    mount_spa(app, settings.frontend_dir)

    return app


app = create_app()


def main() -> None:
    """``uv run attendance`` — local development server with reload."""
    # S104 is suppressed below because binding all interfaces is required inside
    # a container — the port is only reachable via whatever the compose file or
    # task definition chooses to publish.
    uvicorn.run("attendance.main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104


if __name__ == "__main__":
    main()
