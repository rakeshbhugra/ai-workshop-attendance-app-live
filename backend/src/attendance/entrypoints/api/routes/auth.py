"""Sign-in over OpenID Connect, one route set for every provider.

The cookie flags are the security surface: httponly (no script can read it),
samesite=lax (sent on the top-level redirect back from the provider, not on
cross-site POSTs) and secure behind HTTPS. Change one only after reading why.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from attendance.bootstrap import get_auth_service
from attendance.config.settings import SESSION_COOKIE, Settings, get_settings
from attendance.domain.exceptions import AuthenticationError
from attendance.domain.user import User
from attendance.entrypoints.api.schemas.auth import UserOut
from attendance.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE = "attendance_live_oauth_state"


async def current_user(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """The signed-in user, or 401."""
    return await service.current_user(session)


def _callback_uri(request: Request, provider: str, settings: Settings) -> str:
    path = request.url_for("auth_callback", provider=provider).path
    base = settings.public_url.rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}{path}"


def _set(response: Response, name: str, value: str, max_age: int, settings: Settings) -> None:
    response.set_cookie(
        name, value, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=max_age
    )


@router.get("/providers")
async def providers(service: AuthService = Depends(get_auth_service)) -> list[str]:
    return service.provider_names()


@router.get("/{provider}/login")
async def login(
    provider: str,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    url = await service.start(
        provider, redirect_uri=_callback_uri(request, provider, settings), state=state
    )
    response = RedirectResponse(url)
    _set(response, STATE_COOKIE, state, 600, settings)
    return response


@router.get("/{provider}/callback", name="auth_callback")
async def callback(
    provider: str,
    request: Request,
    code: str = "",
    state: str = "",
    oauth_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    # The state cookie is what stops someone finishing a sign-in they did not start.
    if not code or not state or not secrets.compare_digest(state, oauth_state or ""):
        raise AuthenticationError("invalid sign-in attempt")
    _, token = await service.complete(
        provider,
        code,
        redirect_uri=_callback_uri(request, provider, settings),
        now=datetime.now(UTC),
    )
    response = RedirectResponse(f"{settings.public_url.rstrip('/')}/")
    _set(response, SESSION_COOKIE, token, settings.session_max_age_seconds, settings)
    response.delete_cookie(STATE_COOKIE)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: Settings = Depends(get_settings)) -> None:
    # Same flags as when it was set, or the browser treats it as a different cookie.
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, samesite="lax", secure=settings.cookie_secure
    )


@router.get("/me")
async def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.from_domain(user)
