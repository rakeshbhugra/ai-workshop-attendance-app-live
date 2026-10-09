from __future__ import annotations

from httpx import AsyncClient

from attendance.config.settings import SESSION_COOKIE
from attendance.entrypoints.api.routes.auth import STATE_COOKIE


async def test_dev_login_round_trip_sets_session_and_me_works(anonymous: AsyncClient):
    assert (await anonymous.get("/api/v1/auth/me")).status_code == 401
    assert (await anonymous.get("/api/v1/notes")).status_code == 401
    assert "dev" in (await anonymous.get("/api/v1/auth/providers")).json()

    login = await anonymous.get("/api/v1/auth/dev/login")
    assert login.status_code == 307 and STATE_COOKIE in login.cookies
    # The dev provider bounces straight back to the callback with a code.
    callback = await anonymous.get(login.headers["location"])
    assert callback.status_code == 307 and callback.headers["location"] == "/"
    assert SESSION_COOKIE in callback.cookies

    me = await anonymous.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "dev@localhost"
    assert (await anonymous.get("/api/v1/notes")).status_code == 200

    assert (await anonymous.post("/api/v1/auth/logout")).status_code == 204
    assert (await anonymous.get("/api/v1/auth/me")).status_code == 401


async def test_callback_with_wrong_state_is_refused(anonymous: AsyncClient):
    await anonymous.get("/api/v1/auth/dev/login")
    bad = await anonymous.get("/api/v1/auth/dev/callback", params={"code": "dev", "state": "no"})
    assert bad.status_code == 401


async def test_unknown_provider_is_404(anonymous: AsyncClient):
    assert (await anonymous.get("/api/v1/auth/github/login")).status_code == 404
