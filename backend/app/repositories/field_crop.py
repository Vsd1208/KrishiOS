"""Field crop repository for crop history persistence."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field_crop import FieldCrop
from app.repositories.base import BaseRepository


class FieldCropRepository(BaseRepository[FieldCrop]):
    """Persistence operations for field crop history."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FieldCrop)

    async def get_by_field_crop_and_sowing_date(
        self,
        field_id: int,
        crop_id: int,
        sowing_date: date,
    ) -> FieldCrop | None:
        statement = select(FieldCrop).where(
            FieldCrop.field_id == field_id,
            FieldCrop.crop_id == crop_id,
            FieldCrop.sowing_date == sowing_date,
            FieldCrop.deleted_at.is_(None),
        )
        return await self._scalar_one_or_none(statement)

