"""Wire shape for the signed-in user."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from attendance.domain.user import User
from attendance.entrypoints.api.schemas.common import UtcDatetime


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: UtcDatetime

    @classmethod
    def from_domain(cls, user: User) -> UserOut:
        return cls(id=user.id, email=user.email, name=user.name, created_at=user.created_at)
