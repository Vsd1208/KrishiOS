"""Crop business service for catalog management."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.crop import Crop
from app.repositories.crop import CropRepository
from app.schemas.crop import CropCreate, CropUpdate
from app.services.base import BaseService


class CropService(BaseService):
    """Application service for crop catalog operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.crops = CropRepository(session)

    async def create_crop(self, payload: CropCreate) -> Crop:
        existing = await self.crops.get_by_name_and_season(payload.crop_name, payload.season)
        if existing is not None:
            raise EntityConflictError("Crop already exists for this season")
        crop = await self.crops.create(payload.model_dump())
        await self._commit()
        return crop

    async def update_crop(self, crop_id: int, payload: CropUpdate) -> Crop:
        crop = await self.get_crop(crop_id)
        values = payload.model_dump(exclude_unset=True)
        if "crop_name" in values or "season" in values:
            crop_name = values.get("crop_name", crop.crop_name)
            season = values.get("season", crop.season)
            existing = await self.crops.get_by_name_and_season(crop_name, season)
            if existing is not None and existing.id != crop.id:
                raise EntityConflictError("Crop already exists for this season")
        updated = await self.crops.update(crop, values)
        await self._commit()
        return updated

    async def list_crops(self, *, offset: int = 0, limit: int = 100) -> Sequence[Crop]:
        return await self.crops.list(offset=offset, limit=limit)

    async def get_crop(self, crop_id: int) -> Crop:
        return await self._get_required(self.crops, crop_id, "Crop")  # type: ignore[return-value]

    async def delete_crop(self, crop_id: int) -> None:
        crop = await self.get_crop(crop_id)
        await self.crops.soft_delete(crop)
        await self._commit()

