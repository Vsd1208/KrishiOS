"""Field business service for farmer plot management."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityConflictError
from app.models.field import Field
from app.repositories.farmer import FarmerRepository
from app.repositories.field import FieldRepository
from app.schemas.field import FieldCreate, FieldUpdate
from app.services.base import BaseService


class FieldService(BaseService):
    """Application service for field lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.fields = FieldRepository(session)
        self.farmers = FarmerRepository(session)

    async def register_field(self, payload: FieldCreate) -> Field:
        await self._get_required(self.farmers, payload.farmer_id, "Farmer")
        existing = await self.fields.get_by_farmer_and_name(payload.farmer_id, payload.field_name)
        if existing is not None:
            raise EntityConflictError("Field name already exists for this farmer")
        field = await self.fields.create(payload.model_dump())
        await self._commit()
        return field

    async def update_field(self, field_id: int, payload: FieldUpdate) -> Field:
        field = await self.get_field(field_id)
        values = payload.model_dump(exclude_unset=True)
        farmer_id = values.get("farmer_id", field.farmer_id)
        if "farmer_id" in values:
            await self._get_required(self.farmers, values["farmer_id"], "Farmer")
        if "farmer_id" in values or "field_name" in values:
            field_name = values.get("field_name", field.field_name)
            existing = await self.fields.get_by_farmer_and_name(farmer_id, field_name)
            if existing is not None and existing.id != field.id:
                raise EntityConflictError("Field name already exists for this farmer")
        updated = await self.fields.update(field, values)
        await self._commit()
        return updated

    async def list_fields(self, *, offset: int = 0, limit: int = 100) -> Sequence[Field]:
        return await self.fields.list(offset=offset, limit=limit)

    async def get_field(self, field_id: int) -> Field:
        return await self._get_required(self.fields, field_id, "Field")  # type: ignore[return-value]

    async def delete_field(self, field_id: int) -> None:
        field = await self.get_field(field_id)
        await self.fields.soft_delete(field)
        await self._commit()

