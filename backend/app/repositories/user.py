"""User repository."""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Persistence operations for users."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        statement = select(User).where(User.uuid == uuid)
        return await self._scalar_one_or_none(statement)

    async def get_by_phone(self, phone: str) -> User | None:
        statement = select(User).where(User.phone == phone)
        return await self._scalar_one_or_none(statement)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return await self._scalar_one_or_none(statement)
