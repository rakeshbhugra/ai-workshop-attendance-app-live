"""One adapter for every OpenID Connect provider. Providers differ only in
their issuer, which is read from the discovery document.

No JWT library: after the code exchange we call the provider's userinfo
endpoint over TLS, so the answer needs no signature check. Adding a provider
is a new entry in ``ISSUERS`` plus its client id and secret in settings."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from attendance.config.logging import get_logger
from attendance.domain.exceptions import AuthenticationError
from attendance.domain.user import ExternalIdentity
from attendance.ports.auth import IdentityProvider

log = get_logger(__name__)

ISSUERS = {
    "google": "https://accounts.google.com",
}


class OidcProvider(IdentityProvider):
    def __init__(
        self,
        name: str,
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        scope: str = "openid email profile",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.name = name
        self._issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._timeout = timeout_seconds
        self._config: dict[str, Any] | None = None

    async def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        config = await self._discover()
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self._scope,
            "state": state,
            # Always show the account picker; otherwise the browser's last
            # account is signed in silently.
            "prompt": "select_account",
        }
        return f"{config['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(self, code: str, *, redirect_uri: str) -> ExternalIdentity:
        config = await self._discover()
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            token = await http.post(
                config["token_endpoint"],
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token.is_error:
                # The body names the real problem (redirect_uri_mismatch,
                # invalid_grant). Logged, never returned: it can echo the code.
                log.warning("oidc_token_failed", provider=self.name, status=token.status_code)
                raise AuthenticationError(f"{self.name} rejected the sign-in code")
            access = token.json().get("access_token")
            if not access:
                raise AuthenticationError(f"{self.name} returned no access token")
            profile = await http.get(
                config["userinfo_endpoint"], headers={"Authorization": f"Bearer {access}"}
            )
            if profile.is_error:
                log.warning("oidc_userinfo_failed", provider=self.name, status=profile.status_code)
                raise AuthenticationError(f"{self.name} profile could not be read")
            info = dict(profile.json())
        email = str(info.get("email") or "")
        if not info.get("sub") or not email:
            raise AuthenticationError(f"{self.name} returned no email address")
        return ExternalIdentity(
            provider=self.name,
            subject=str(info["sub"]),
            email=email,
            name=str(info.get("name") or ""),
            email_verified=bool(info.get("email_verified", False)),
        )

    async def _discover(self) -> dict[str, Any]:
        if self._config is None:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                r = await http.get(f"{self._issuer}/.well-known/openid-configuration")
                r.raise_for_status()
                self._config = dict(r.json())
        return self._config
