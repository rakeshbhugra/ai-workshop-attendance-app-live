from functools import partial
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from attendance.adapters.auth import oidc
from attendance.domain.exceptions import AuthenticationError


@pytest.mark.parametrize("failure", [None, "token", "no_token", "profile", "no_email"])
async def test_google_code_exchange_uses_trusted_userinfo(monkeypatch, failure):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://accounts.google.com/authorize",
                    "token_endpoint": "https://oauth2.googleapis.com/token",
                    "userinfo_endpoint": "https://openidconnect.googleapis.com/userinfo",
                },
            )
        if request.url.path == "/token":
            assert b"grant_type=authorization_code" in request.content
            if failure == "token":
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(
                200, json={} if failure == "no_token" else {"access_token": "test-access-token"}
            )
        assert request.headers["authorization"] == "Bearer test-access-token"
        if failure == "profile":
            return httpx.Response(401, json={"error": "unauthorized"})
        return httpx.Response(
            200,
            json={
                "sub": "google-subject",
                "name": "Alice",
                "email": "" if failure == "no_email" else "alice@example.com",
                "email_verified": True,
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        oidc.httpx, "AsyncClient", partial(original, transport=httpx.MockTransport(handler))
    )
    provider = oidc.OidcProvider(
        "google",
        issuer="https://accounts.google.com",
        client_id="test-client",
        client_secret="test-secret",
    )
    url = await provider.authorization_url(redirect_uri="http://localhost/callback", state="random")
    params = parse_qs(urlparse(url).query)
    assert params["state"] == ["random"]
    assert params["scope"] == ["openid email profile"]
    if failure:
        with pytest.raises(AuthenticationError):
            await provider.exchange_code("test-code", redirect_uri="http://localhost/callback")
    else:
        identity = await provider.exchange_code(
            "test-code", redirect_uri="http://localhost/callback"
        )
        assert identity.subject == "google-subject" and identity.email_verified
