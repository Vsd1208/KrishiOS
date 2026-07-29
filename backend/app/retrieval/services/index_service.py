"""Application service for retrieval index management APIs."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrieval_index import RetrievalIndexVersion
from app.retrieval.api.schemas import (
    IndexBuildRequest,
    IndexResponse,
    IndexStatusResponse,
)
from app.retrieval.indexing.manager import IndexManager


class RetrievalIndexService:
    """Use-case service for building, promoting, rolling back, and listing indexes."""

    def __init__(self, session: AsyncSession, index_manager: IndexManager) -> None:
        self._session = session
        self._index_manager = index_manager

    async def build(self, request: IndexBuildRequest) -> RetrievalIndexVersion:
        """Build and validate a new immutable retrieval index."""
        return await self._index_manager.build_index(
            alias_name=request.alias_name,
            index_kind=request.index_kind,
            build_mode=request.build_mode,
            source_document_type=request.source_document_type,
        )

    async def promote(self, index_id: int) -> RetrievalIndexVersion:
        """Promote a validated index using alias switching."""
        return await self._index_manager.promote_index(index_id)

    async def rollback(self, alias_name: str) -> RetrievalIndexVersion:
        """Rollback an alias to the previous retained production index."""
        return await self._index_manager.rollback(alias_name)

    async def list_indexes(self) -> list[RetrievalIndexVersion]:
        """List all retrieval index versions."""
        return await self._index_manager.list_indexes()

    async def status(self, alias_name: str) -> IndexStatusResponse:
        """Return current alias status and version history."""
        active_collection, active, previous, indexes = await self._index_manager.status(alias_name)
        return IndexStatusResponse(
            alias_name=alias_name,
            active_collection=active_collection,
            active_index=IndexResponse.model_validate(active) if active else None,
            previous_index=IndexResponse.model_validate(previous) if previous else None,
            indexes=[IndexResponse.model_validate(index) for index in indexes],
        )

