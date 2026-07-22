"""Soil sample repository for collection workflow persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soil_sample import SoilSample
from app.repositories.base import BaseRepository


class SoilSampleRepository(BaseRepository[SoilSample]):
    """Persistence operations for soil samples."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SoilSample)

