"""Reusable asynchronous repository primitives for SQLAlchemy models."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository containing persistence-only CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def create(self, values: Mapping[str, Any]) -> ModelT:
        entity = self.model(**values)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get(self, entity_id: Any, *, include_deleted: bool = False) -> ModelT | None:
        primary_key = inspect(self.model).primary_key[0]
        statement = select(self.model).where(primary_key == entity_id)
        statement = self._filter_deleted(statement, include_deleted=include_deleted)
        return await self._scalar_one_or_none(statement)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> Sequence[ModelT]:
        statement = select(self.model).offset(offset).limit(limit)
        statement = self._filter_deleted(statement, include_deleted=include_deleted)
        result = await self.session.scalars(statement)
        return result.all()

    async def update(self, entity: ModelT, values: Mapping[str, Any]) -> ModelT:
        for field_name, value in values.items():
            setattr(entity, field_name, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def soft_delete(self, entity: ModelT) -> ModelT:
        setattr(entity, "deleted_at", datetime.now(UTC))
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def exists(self, entity_id: Any) -> bool:
        return await self.get(entity_id) is not None

    def _filter_deleted(
        self,
        statement: Select[tuple[ModelT]],
        *,
        include_deleted: bool,
    ) -> Select[tuple[ModelT]]:
        if include_deleted or not hasattr(self.model, "deleted_at"):
            return statement
        return statement.where(self.model.deleted_at.is_(None))

    async def _scalar_one_or_none(self, statement: Select[tuple[ModelT]]) -> ModelT | None:
        result = await self.session.scalars(statement)
        return result.one_or_none()
