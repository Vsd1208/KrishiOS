"""Soil sample repository for collection workflow persistence."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soil_sample import SoilSample
from app.repositories.base import BaseRepository


class SoilSampleRepository(BaseRepository[SoilSample]):
    """Persistence operations for soil samples."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SoilSample)

    async def list_by_farmer(self, farmer_id: int, *, offset: int = 0,
                             limit: int = 100) -> Sequence[SoilSample]:
        """Soil samples of one farmer (used to scope a farmer's own reads)."""
        statement = (select(SoilSample).where(SoilSample.farmer_id == farmer_id)
                     .order_by(SoilSample.sample_id).offset(offset).limit(limit))
        return (await self.session.scalars(statement)).all()
