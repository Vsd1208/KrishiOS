"""Field crop business service for crop assignment and history."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.field_crop import FieldCrop
from app.repositories.crop import CropRepository
from app.repositories.field import FieldRepository
from app.repositories.field_crop import FieldCropRepository
from app.schemas.field_crop import FieldCropCreate, FieldCropUpdate
from app.services.base import BaseService


class FieldCropService(BaseService):
    """Application service for assigning crops to fields."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.field_crops = FieldCropRepository(session)
        self.fields = FieldRepository(session)
        self.crops = CropRepository(session)

    async def assign_crop(self, payload: FieldCropCreate) -> FieldCrop:
        await self._get_required(self.fields, payload.field_id, "Field")
        await self._get_required(self.crops, payload.crop_id, "Crop")
        existing = await self.field_crops.get_by_field_crop_and_sowing_date(
            payload.field_id,
            payload.crop_id,
            payload.sowing_date,
        )
        if existing is not None:
            raise EntityConflictError("Crop is already assigned to this field for the sowing date")
        field_crop = await self.field_crops.create(payload.model_dump())
        await self._commit()
        return field_crop

    async def update_field_crop(self, field_crop_id: int, payload: FieldCropUpdate) -> FieldCrop:
        field_crop = await self.get_field_crop(field_crop_id)
        values = payload.model_dump(exclude_unset=True)
        if "crop_id" in values:
            await self._get_required(self.crops, values["crop_id"], "Crop")
        crop_id = values.get("crop_id", field_crop.crop_id)
        sowing_date = values.get("sowing_date", field_crop.sowing_date)
        existing = await self.field_crops.get_by_field_crop_and_sowing_date(
            field_crop.field_id,
            crop_id,
            sowing_date,
        )
        if existing is not None and existing.id != field_crop.id:
            raise EntityConflictError("Crop is already assigned to this field for the sowing date")
        updated = await self.field_crops.update(field_crop, values)
        await self._commit()
        return updated

    async def list_field_crops(self, *, offset: int = 0, limit: int = 100) -> Sequence[FieldCrop]:
        return await self.field_crops.list(offset=offset, limit=limit)

    async def get_field_crop(self, field_crop_id: int) -> FieldCrop:
        return await self._get_required(  # type: ignore[return-value]
            self.field_crops,
            field_crop_id,
            "FieldCrop",
        )

    async def delete_field_crop(self, field_crop_id: int) -> None:
        field_crop = await self.get_field_crop(field_crop_id)
        await self.field_crops.soft_delete(field_crop)
        await self._commit()
