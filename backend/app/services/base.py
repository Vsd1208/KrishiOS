"""Shared service helpers for transaction management and entity lookup."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base
from app.exceptions.domain import EntityConflictError, EntityNotFoundError
from app.repositories.base import BaseRepository


class BaseService:
    """Base service with reusable transaction and lookup behavior."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise EntityConflictError("Request violates a database constraint") from exc

    async def _get_required(
        self,
        repository: BaseRepository[Any],
        entity_id: Any,
        entity_name: str,
    ) -> Base:
        entity = await repository.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"{entity_name} not found")
        return entity

    async def _list(
        self,
        repository: BaseRepository[Any],
        *,
        offset: int,
        limit: int,
    ) -> Sequence[Base]:
        return await repository.list(offset=offset, limit=limit)

