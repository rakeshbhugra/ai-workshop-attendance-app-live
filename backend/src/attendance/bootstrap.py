"""Composition root — the one file that knows which adapter is which.

Everything else in the app depends on ports. This module picks the concrete
implementations and hands them to services through FastAPI's ``Depends``. That
is why swapping Postgres for something else, or S3 for GCS, is a change to *this
file plus one new adapter* rather than a change to every service.

Two lifetimes live here, deliberately:

* **Process-wide singletons** (object storage) — built once at import, because an
  S3 client holds a connection pool you do not want to rebuild per request.
* **Request-scoped objects** (session → UoW → service) — built per request by
  the ``Depends`` chain, because a transaction must not outlive its request.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.auth.dev import DevProvider
from attendance.adapters.auth.oidc import ISSUERS, OidcProvider
from attendance.adapters.auth.tokens import SignedSessionTokens
from attendance.adapters.storage import build_object_storage
from attendance.adapters.unit_of_work import SqlAlchemyUnitOfWork
from attendance.config.database import get_db
from attendance.config.settings import get_settings
from attendance.ports.auth import IdentityProvider, SessionTokens
from attendance.ports.object_storage import ObjectStorage
from attendance.ports.unit_of_work import UnitOfWork
from attendance.services.attendance import AttendanceService
from attendance.services.auth import AuthService
from attendance.services.files import FileService
from attendance.services.notes import NoteService

# ── process-wide singletons ──────────────────────────────────────────────────
_object_storage: ObjectStorage = build_object_storage(get_settings())


def get_object_storage() -> ObjectStorage:
    return _object_storage


# ── request-scoped chain ─────────────────────────────────────────────────────
def get_unit_of_work(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_attendance_service(uow: UnitOfWork = Depends(get_unit_of_work)) -> AttendanceService:
    return AttendanceService(uow)


def get_note_service(uow: UnitOfWork = Depends(get_unit_of_work)) -> NoteService:
    return NoteService(uow)


def get_file_service(storage: ObjectStorage = Depends(get_object_storage)) -> FileService:
    return FileService(storage)


def get_providers() -> dict[str, IdentityProvider]:
    """The sign-in methods switched on by settings, in button order."""
    s = get_settings()
    providers: dict[str, IdentityProvider] = {}
    if s.google_client_id:
        providers["google"] = OidcProvider(
            "google",
            issuer=ISSUERS["google"],
            client_id=s.google_client_id,
            client_secret=s.google_client_secret,
        )
    if s.auth_dev_login:
        if s.environment in {"staging", "prod"}:
            raise RuntimeError("ATTENDANCE_AUTH_DEV_LOGIN must be false in staging and prod")
        providers["dev"] = DevProvider()
    return providers


def get_session_tokens() -> SessionTokens:
    s = get_settings()
    if s.environment in {"staging", "prod"} and s.session_secret == "dev-session-secret":  # noqa: S105
        raise RuntimeError("ATTENDANCE_SESSION_SECRET must be set in staging and prod")
    return SignedSessionTokens(s.session_secret, max_age_seconds=s.session_max_age_seconds)


def get_auth_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
    providers: dict[str, IdentityProvider] = Depends(get_providers),
    sessions: SessionTokens = Depends(get_session_tokens),
) -> AuthService:
    domains = frozenset(d.lower() for d in get_settings().allowed_email_domains)
    emails = frozenset(e.strip().lower() for e in get_settings().allowed_staff_emails)
    return AuthService(uow, providers, sessions, allowed_domains=domains, allowed_emails=emails)
