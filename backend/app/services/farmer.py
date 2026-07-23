"""Farmer business service for registration and profile management."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.farmer import Farmer
from app.repositories.district import DistrictRepository
from app.repositories.farmer import FarmerRepository
from app.schemas.farmer import FarmerCreate, FarmerUpdate
from app.services.base import BaseService


class FarmerService(BaseService):
    """Application service for farmer lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.farmers = FarmerRepository(session)
        self.districts = DistrictRepository(session)

    async def register_farmer(self, payload: FarmerCreate) -> Farmer:
        await self._get_required(self.districts, payload.district_id, "District")
        if await self.farmers.get_by_phone(payload.phone) is not None:
            raise EntityConflictError("Farmer phone number is already registered")
        farmer = await self.farmers.create(payload.model_dump())
        await self._commit()
        return farmer

    async def update_farmer(self, farmer_id: int, payload: FarmerUpdate) -> Farmer:
        farmer = await self.get_farmer(farmer_id)
        values = payload.model_dump(exclude_unset=True)
        if "district_id" in values:
            await self._get_required(self.districts, values["district_id"], "District")
        if "phone" in values:
            existing = await self.farmers.get_by_phone(values["phone"])
            if existing is not None and existing.id != farmer.id:
                raise EntityConflictError("Farmer phone number is already registered")
        updated = await self.farmers.update(farmer, values)
        await self._commit()
        return updated

    async def list_farmers(self, *, offset: int = 0, limit: int = 100) -> Sequence[Farmer]:
        return await self.farmers.list(offset=offset, limit=limit)

    async def get_farmer(self, farmer_id: int) -> Farmer:
        return await self._get_required(  # type: ignore[return-value]
            self.farmers,
            farmer_id,
            "Farmer",
        )

    async def delete_farmer(self, farmer_id: int) -> None:
        farmer = await self.get_farmer(farmer_id)
        await self.farmers.soft_delete(farmer)
        await self._commit()
