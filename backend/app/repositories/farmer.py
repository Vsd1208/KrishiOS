"""Farmer repository with farmer-specific data access queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farmer import Farmer
from app.repositories.base import BaseRepository


class FarmerRepository(BaseRepository[Farmer]):
    """Persistence operations for farmers."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Farmer)

    async def get_by_phone(self, phone: str) -> Farmer | None:
        statement = select(Farmer).where(Farmer.phone == phone, Farmer.deleted_at.is_(None))
        return await self._scalar_one_or_none(statement)

