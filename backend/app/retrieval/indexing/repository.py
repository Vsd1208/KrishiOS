"""Database repositories for retrieval index state."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.knowledge_document import (
    DocumentStatus,
    KnowledgeDocument,
)
from app.models.retrieval_index import (
    IndexedDocumentState,
    RetrievalIndexStatus,
    RetrievalIndexVersion,
)


class RetrievalIndexRepository:
    """Persistence operations for retrieval index versions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_version_number(self, alias_name: str) -> int:
        """Return the next monotonically increasing version number for an alias."""
        statement = (
            select(RetrievalIndexVersion.version_number)
            .where(RetrievalIndexVersion.alias_name == alias_name)
            .order_by(desc(RetrievalIndexVersion.version_number))
            .limit(1)
        )

        current = await self.session.scalar(statement)
        return int(current or 0) + 1

    async def create(
        self,
        index: RetrievalIndexVersion,
    ) -> RetrievalIndexVersion:
        """Persist a new retrieval index version."""
        self.session.add(index)
        await self.session.flush()
        await self.session.refresh(index)
        return index

    async def get(
        self,
        index_id: int,
    ) -> RetrievalIndexVersion | None:
        """Load an index version by primary key."""
        return await self.session.get(
            RetrievalIndexVersion,
            index_id,
        )

    async def list(self) -> Sequence[RetrievalIndexVersion]:
        """List index versions newest first."""
        result = await self.session.scalars(
            select(RetrievalIndexVersion).order_by(
                desc(RetrievalIndexVersion.created_at)
            )
        )
        return result.all()

    async def active_for_alias(
        self,
        alias_name: str,
    ) -> RetrievalIndexVersion | None:
        """Return the active production index for an alias."""
        result = await self.session.scalars(
            select(RetrievalIndexVersion)
            .where(
                RetrievalIndexVersion.alias_name == alias_name,
                RetrievalIndexVersion.status == RetrievalIndexStatus.ACTIVE,
            )
            .order_by(desc(RetrievalIndexVersion.promoted_at))
            .limit(1)
        )
        return result.one_or_none()

    async def previous_active_for_alias(
        self,
        alias_name: str,
    ) -> RetrievalIndexVersion | None:
        """Return the previous active index retained for instant rollback."""
        result = await self.session.scalars(
            select(RetrievalIndexVersion)
            .where(
                RetrievalIndexVersion.alias_name == alias_name,
                RetrievalIndexVersion.status == RetrievalIndexStatus.ROLLED_BACK,
            )
            .order_by(desc(RetrievalIndexVersion.rolled_back_at))
            .limit(1)
        )
        return result.one_or_none()

    async def states_for_index(
        self,
        index_id: int,
    ) -> Sequence[IndexedDocumentState]:
        """Return document indexing states for an index version."""
        result = await self.session.scalars(
            select(IndexedDocumentState).where(
                IndexedDocumentState.index_version_id == index_id
            )
        )
        return result.all()

    async def mark_status(
        self,
        index: RetrievalIndexVersion,
        status: RetrievalIndexStatus,
        failure_reason: str | None = None,
    ) -> RetrievalIndexVersion:
        """Update index lifecycle status."""
        index.status = status
        index.failure_reason = failure_reason

        await self.session.flush()
        await self.session.refresh(index)

        return index

    async def promote(
        self,
        new_index: RetrievalIndexVersion,
        previous_index: RetrievalIndexVersion | None,
    ) -> RetrievalIndexVersion:
        """Mark a validated index active and retain the previous index for rollback."""
        now = datetime.now(UTC)

        if previous_index is not None and previous_index.id != new_index.id:
            previous_index.status = RetrievalIndexStatus.ROLLED_BACK
            previous_index.rolled_back_at = now

        new_index.status = RetrievalIndexStatus.ACTIVE
        new_index.promoted_at = now

        await self.session.flush()
        await self.session.refresh(new_index)

        return new_index

    async def save_document_states(
        self,
        states: Sequence[IndexedDocumentState],
    ) -> None:
        """Persist incremental indexing state rows."""
        self.session.add_all(states)
        await self.session.flush()


class RetrievalDocumentRepository:
    """Read access to documents and chunks for retrieval indexing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        document_id: int,
    ) -> KnowledgeDocument | None:
        """Return a knowledge document by its database ID."""

        result = await self.session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
            )
        )

        return result.one_or_none()

    async def load_chunks_for_document(
        self,
        document_id: int,
    ) -> Sequence[DocumentChunk]:
        """Return all chunks belonging to a single document."""

        result = await self.session.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
            )
            .order_by(
                DocumentChunk.chunk_index,
            )
        )

        return result.all()

    async def load_indexable_chunks(
        self,
        document_type: str | None = None,
    ) -> Sequence[tuple[DocumentChunk, KnowledgeDocument]]:
        """Load chunks from completed documents eligible for retrieval indexing."""

        statement = (
            select(DocumentChunk, KnowledgeDocument)
            .join(
                KnowledgeDocument,
                DocumentChunk.document_id == KnowledgeDocument.id,
            )
            .where(
                KnowledgeDocument.status == DocumentStatus.COMPLETED,
            )
            .order_by(
                KnowledgeDocument.id,
                DocumentChunk.chunk_index,
            )
        )

        if document_type is not None:
            statement = statement.where(
                KnowledgeDocument.document_type == document_type
            )

        result = await self.session.execute(statement)

        return result.all()