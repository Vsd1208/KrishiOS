"""Officer repository with officer-specific data access queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.officer import Officer
from app.repositories.base import BaseRepository


class OfficerRepository(BaseRepository[Officer]):
    """Persistence operations for officers."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Officer)

    async def get_by_email(self, email: str) -> Officer | None:
        statement = select(Officer).where(Officer.email == email, Officer.deleted_at.is_(None))
        return await self._scalar_one_or_none(statement)

    async def get_by_phone(self, phone: str) -> Officer | None:
        statement = select(Officer).where(Officer.phone == phone, Officer.deleted_at.is_(None))
        return await self._scalar_one_or_none(statement)

