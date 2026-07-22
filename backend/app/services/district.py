"""District business service for geographic reference data."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.district import District
from app.repositories.district import DistrictRepository
from app.schemas.district import DistrictCreate, DistrictUpdate
from app.services.base import BaseService


class DistrictService(BaseService):
    """Application service for district lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.districts = DistrictRepository(session)

    async def create_district(self, payload: DistrictCreate) -> District:
        existing = await self.districts.get_by_state_and_name(payload.state, payload.district_name)
        if existing is not None:
            raise EntityConflictError("District already exists for this state")
        district = await self.districts.create(payload.model_dump())
        await self._commit()
        return district

    async def update_district(self, district_id: int, payload: DistrictUpdate) -> District:
        district = await self.get_district(district_id)
        values = payload.model_dump(exclude_unset=True)
        if "state" in values or "district_name" in values:
            state = values.get("state", district.state)
            district_name = values.get("district_name", district.district_name)
            existing = await self.districts.get_by_state_and_name(state, district_name)
            if existing is not None and existing.id != district.id:
                raise EntityConflictError("District already exists for this state")
        updated = await self.districts.update(district, values)
        await self._commit()
        return updated

    async def list_districts(self, *, offset: int = 0, limit: int = 100) -> Sequence[District]:
        return await self.districts.list(offset=offset, limit=limit)

    async def get_district(self, district_id: int) -> District:
        return await self._get_required(self.districts, district_id, "District")  # type: ignore[return-value]

    async def delete_district(self, district_id: int) -> None:
        district = await self.get_district(district_id)
        await self.districts.soft_delete(district)
        await self._commit()

