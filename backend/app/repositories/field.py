"""Field repository with farmer-field data access queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field import Field
from app.repositories.base import BaseRepository


class FieldRepository(BaseRepository[Field]):
    """Persistence operations for fields."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Field)

    async def get_by_farmer_and_name(self, farmer_id: int, field_name: str) -> Field | None:
        statement = select(Field).where(
            Field.farmer_id == farmer_id,
            Field.field_name == field_name,
            Field.deleted_at.is_(None),
        )
        return await self._scalar_one_or_none(statement)

