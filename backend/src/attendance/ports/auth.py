"""Ports: identity providers and session tokens, in our vocabulary not theirs."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from attendance.domain.user import ExternalIdentity


class IdentityProvider(ABC):
    name: str

    @abstractmethod
    async def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        """Where to send the browser. ``state`` is echoed back and checked."""

    @abstractmethod
    async def exchange_code(self, code: str, *, redirect_uri: str) -> ExternalIdentity:
        """Trade the callback code for a verified identity.
        Raises AuthenticationError if the provider rejects it."""


class SessionTokens(ABC):
    @abstractmethod
    def issue(self, user_id: uuid.UUID) -> str:
        """An opaque token safe to put in a cookie."""

    @abstractmethod
    def read(self, token: str) -> uuid.UUID | None:
        """The user id, or None if forged, tampered or expired."""
