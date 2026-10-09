"""SQLAlchemy implementation of UserRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from attendance.adapters.orm.tables import identity_table, user_table
from attendance.domain.user import Identity, User
from attendance.ports.repositories import UserRepository


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(user)

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(func.lower(user_table.c.email) == email.lower())
            .order_by(user_table.c.created_at)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_identity(self, provider: str, subject: str) -> User | None:
        stmt = (
            select(User)
            .join(identity_table, identity_table.c.user_id == user_table.c.id)
            .where(identity_table.c.provider == provider, identity_table.c.subject == subject)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def link(self, identity: Identity) -> None:
        self._session.add(identity)
