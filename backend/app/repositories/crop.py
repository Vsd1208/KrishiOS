"""Crop repository with crop catalog data access queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crop import Crop
from app.repositories.base import BaseRepository


class CropRepository(BaseRepository[Crop]):
    """Persistence operations for crop catalog entries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Crop)

    async def get_by_name_and_season(self, crop_name: str, season: str) -> Crop | None:
        statement = select(Crop).where(
            Crop.crop_name == crop_name,
            Crop.season == season,
            Crop.deleted_at.is_(None),
        )
        return await self._scalar_one_or_none(statement)

