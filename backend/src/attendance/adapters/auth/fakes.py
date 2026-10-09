"""Test doubles: a provider that vouches for whoever you tell it to, and
plaintext session tokens."""

from __future__ import annotations

import uuid

from attendance.domain.exceptions import AuthenticationError
from attendance.domain.user import ExternalIdentity
from attendance.ports.auth import IdentityProvider, SessionTokens


class FakeProvider(IdentityProvider):
    def __init__(self, name: str, identity: ExternalIdentity | None = None) -> None:
        self.name = name
        self.identity = identity

    async def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        return f"https://{self.name}.example/authorize?state={state}"

    async def exchange_code(self, code: str, *, redirect_uri: str) -> ExternalIdentity:
        if self.identity is None or code != "good":
            raise AuthenticationError(f"{self.name} rejected the code")
        return self.identity


class FakeSessionTokens(SessionTokens):
    def issue(self, user_id: uuid.UUID) -> str:
        return str(user_id)

    def read(self, token: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(token)
        except ValueError:
            return None
