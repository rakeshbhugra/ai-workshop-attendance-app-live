"""Who is signed in. A ``User`` is ours; an ``ExternalIdentity`` is what a
provider vouched for. One user can have many identities (Google today, another
provider tomorrow). Every sign-in method ends by producing an
``ExternalIdentity`` and handing it to ``AuthService.sign_in``; that is the one
door into the user table."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ExternalIdentity:
    provider: str  # "google", "dev", later "password", "email", ...
    subject: str  # stable id at that provider
    email: str
    name: str
    email_verified: bool = False


@dataclass
class User:
    email: str
    name: str
    created_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def register(cls, identity: ExternalIdentity, now: datetime) -> User:
        return cls(email=identity.email, name=identity.name or identity.email, created_at=now)


@dataclass
class Identity:
    """The link row: this provider's subject belongs to this user."""

    provider: str
    subject: str
    user_id: uuid.UUID
    created_at: datetime
