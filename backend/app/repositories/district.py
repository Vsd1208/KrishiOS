"""District repository with geography-specific data access queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.district import District
from app.repositories.base import BaseRepository


class DistrictRepository(BaseRepository[District]):
    """Persistence operations for districts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, District)

    async def get_by_state_and_name(self, state: str, district_name: str) -> District | None:
        statement = select(District).where(
            District.state == state,
            District.district_name == district_name,
            District.deleted_at.is_(None),
        )
        return await self._scalar_one_or_none(statement)

