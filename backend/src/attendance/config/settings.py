"""Application settings, loaded from the environment (and a local .env).

Every setting has a default that makes a fresh clone run. Nothing here should
ever hold a real secret — production values arrive as environment variables.

Naming: the ``ATTENDANCE_`` prefix keeps these from colliding with anything else in a
container's environment. ``make init NAME=...`` rewrites it.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# The sign-in cookie's name.
SESSION_COOKIE = "attendance_live_session"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ATTENDANCE_", extra="ignore")

    app_name: str = "Attendance"
    environment: str = "local"  # local | dev | staging | prod
    debug: bool = False

    # ── database ────────────────────────────────────────────────────────────
    # Postgres is the default, NOT a requirement. Three tiers — see
    # docs/database.md:
    #   Postgres      the compose stacks set this; concurrent writers, >1 instance
    #   SQLite        just change this one line (the whole test suite runs on it)
    #   no database   delete the persistence layers; the doc has the checklist
    #
    # The runtime default is the isolated local Postgres port.
    # Tests explicitly override the connection with in-memory SQLite.
    database_url: str = "postgresql+asyncpg://attendance:attendance@localhost:55433/attendance"
    db_echo: bool = False

    # ── http ────────────────────────────────────────────────────────────────
    # Only needed in dev, where Vite serves the SPA from :5173 and the API is on
    # :8000. In production FastAPI serves both from one origin, so CORS is moot.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Where the built SPA lives. Set in the production image; empty in dev, which
    # turns the static-file mount off entirely.
    frontend_dir: str = ""

    # ── logging ─────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    # Human-readable coloured logs locally, one JSON object per line everywhere
    # else (so CloudWatch/Loki can index the fields instead of regexing strings).
    log_json: bool = False

    # ── object storage (S3 / LocalStack) ────────────────────────────────────
    # Empty bucket = in-memory storage. endpoint_url is only set for LocalStack
    # or MinIO; leave it empty for real AWS S3.
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # ── sign-in ─────────────────────────────────────────────────────────────
    # Google is on when its client id is set. Register the redirect URI
    # <public url>/api/v1/auth/google/callback in the Google Cloud console.
    google_client_id: str = ""
    google_client_secret: str = ""
    # The "dev" provider signs everyone in as a fixed user, so a fresh clone
    # works with no credentials. Refused in staging/prod.
    auth_dev_login: bool = True
    # Lowercase domains, e.g. ["example.com"]. Empty = anyone Google vouches for.
    allowed_email_domains: list[str] = []
    allowed_staff_emails: list[str] = []
    # Signs the session cookie. Rotate it to log everyone out. Override in prod.
    session_secret: str = "dev-session-secret"  # noqa: S105 - dev default, overridden in prod
    session_max_age_seconds: int = 60 * 60 * 24 * 30
    cookie_secure: bool = False  # True behind HTTPS
    # Where the browser lives, for OAuth redirect URIs. Empty = the request's
    # own origin. Set it in dev to http://localhost:5173 so Google sends the
    # browser back through the Vite proxy.
    public_url: str = ""

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


# The process-wide settings. Built on first use so importing this module never
# reads the environment, and replaceable so `create_app(settings)` can install
# what it was handed.
_settings: Settings | None = None


def get_settings() -> Settings:
    """The active settings. Reads the environment once, on first call."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings) -> None:
    """Install settings for the whole process.

    This exists because a cached ``get_settings()`` and an explicitly-passed
    ``Settings`` object are otherwise two different sources of truth: anything
    reaching for ``get_settings()`` deep in the app (the engine, a health check)
    would quietly use the environment while the caller believed its own object
    was in effect. Silent, and very confusing when the two disagree about which
    database to use.

    Called by ``create_app(settings)``. Tests generally go through that.
    """
    global _settings
    _settings = settings
