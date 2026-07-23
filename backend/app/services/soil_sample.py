"""Soil sample business service for collection workflow operations."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityValidationError
from app.models.soil_sample import SoilSample
from app.repositories.farmer import FarmerRepository
from app.repositories.field import FieldRepository
from app.repositories.officer import OfficerRepository
from app.repositories.soil_sample import SoilSampleRepository
from app.schemas.soil_sample import SoilSampleCreate, SoilSampleUpdate
from app.services.base import BaseService


class SoilSampleService(BaseService):
    """Application service for registering and updating soil samples."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.soil_samples = SoilSampleRepository(session)
        self.farmers = FarmerRepository(session)
        self.fields = FieldRepository(session)
        self.officers = OfficerRepository(session)

    async def register_soil_sample(self, payload: SoilSampleCreate) -> SoilSample:
        await self._get_required(self.farmers, payload.farmer_id, "Farmer")
        field = await self._get_required(self.fields, payload.field_id, "Field")
        await self._get_required(self.officers, payload.collector_id, "Officer")
        if field.farmer_id != payload.farmer_id:
            raise EntityValidationError("Field does not belong to the provided farmer")
        sample = await self.soil_samples.create(payload.model_dump())
        await self._commit()
        return sample

    async def update_soil_sample(self, sample_id: int, payload: SoilSampleUpdate) -> SoilSample:
        sample = await self.get_soil_sample(sample_id)
        values = payload.model_dump(exclude_unset=True)
        if "collector_id" in values:
            await self._get_required(self.officers, values["collector_id"], "Officer")
        updated = await self.soil_samples.update(sample, values)
        await self._commit()
        return updated

    async def list_soil_samples(self, *, offset: int = 0, limit: int = 100) -> Sequence[SoilSample]:
        return await self.soil_samples.list(offset=offset, limit=limit)

    async def get_soil_sample(self, sample_id: int) -> SoilSample:
        return await self._get_required(  # type: ignore[return-value]
            self.soil_samples,
            sample_id,
            "SoilSample",
        )

    async def delete_soil_sample(self, sample_id: int) -> None:
        sample = await self.get_soil_sample(sample_id)
        await self.soil_samples.soft_delete(sample)
        await self._commit()
