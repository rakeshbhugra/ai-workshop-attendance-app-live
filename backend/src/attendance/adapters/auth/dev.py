"""Local sign-in with no provider: the login bounces straight back to the
callback and everyone becomes the same fixed user. Bootstrap refuses to wire
it in staging and prod."""

from __future__ import annotations

from urllib.parse import urlencode

from attendance.domain.user import ExternalIdentity
from attendance.ports.auth import IdentityProvider


class DevProvider(IdentityProvider):
    name = "dev"

    def __init__(self, email: str = "dev@localhost", name: str = "Dev User") -> None:
        self._identity = ExternalIdentity(
            provider=self.name, subject=email, email=email, name=name, email_verified=True
        )

    async def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        return f"{redirect_uri}?{urlencode({'code': 'dev', 'state': state})}"

    async def exchange_code(self, code: str, *, redirect_uri: str) -> ExternalIdentity:
        return self._identity
