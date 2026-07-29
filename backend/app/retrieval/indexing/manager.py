"""Enterprise IndexManager for retrieval index lifecycle operations."""

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.domain import EntityNotFoundError, EntityValidationError
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.retrieval_index import (
    IndexedDocumentState,
    RetrievalBuildMode,
    RetrievalIndexKind,
    RetrievalIndexStatus,
    RetrievalIndexVersion,
)
from app.retrieval.deployment.blue_green import BlueGreenDeploymentService
from app.retrieval.indexing.repository import (
    RetrievalDocumentRepository,
    RetrievalIndexRepository,
)
from app.retrieval.interfaces.providers import EmbeddingProvider, VectorStoreProvider
from app.retrieval.interfaces.types import VectorRecord
from app.retrieval.validation.validator import IndexValidator


class IndexManager:
    """Coordinate versioned index builds, validation, promotion, and rollback."""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStoreProvider,
        embedding_provider: EmbeddingProvider,
        index_prefix: str,
    ) -> None:
        self._session = session
        self._indexes = RetrievalIndexRepository(session)
        self._documents = RetrievalDocumentRepository(session)
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._index_prefix = index_prefix
        self._validator = IndexValidator(vector_store)
        self._deployment = BlueGreenDeploymentService(vector_store)

    async def build_index(
        self,
        alias_name: str,
        index_kind: RetrievalIndexKind,
        build_mode: RetrievalBuildMode,
        source_document_type: str | None = None,
    ) -> RetrievalIndexVersion:
        """Build and validate a new immutable retrieval index version."""
        started = perf_counter()
        version_number = await self._indexes.next_version_number(alias_name)
        collection_name = f"{self._index_prefix}-v{version_number:03d}"
        index = await self._indexes.create(
            RetrievalIndexVersion(
                version_number=version_number,
                collection_name=collection_name,
                alias_name=alias_name,
                index_kind=index_kind,
                status=RetrievalIndexStatus.BUILDING,
                build_mode=build_mode,
                embedding_model=self._embedding_provider.model_name,
                embedding_version=self._embedding_provider.model_version,
                vector_size=self._embedding_provider.vector_size,
            )
        )
        await self._session.commit()

        try:
            await self._vector_store.create_collection(collection_name, index.vector_size)
            chunks = await self._documents.load_indexable_chunks(source_document_type)
            records, states = await self._build_records(index, chunks, build_mode, alias_name)
            await self._vector_store.upsert(collection_name, records)

            index.chunk_count = len(records)
            index.document_count = len({state.document_id for state in states})
            await self._indexes.save_document_states(states)
            await self._indexes.mark_status(index, RetrievalIndexStatus.VALIDATING)

            latency_ms = (perf_counter() - started) * 1000
            report = await self._validator.validate(collection_name, len(records), latency_ms)
            index.validation_report = report.to_dict()
            if not report.passed:
                await self._indexes.mark_status(
                    index,
                    RetrievalIndexStatus.FAILED,
                    "Index validation gates did not pass",
                )
            else:
                await self._indexes.mark_status(index, RetrievalIndexStatus.READY)
            await self._session.commit()
            return index
        except Exception as exc:
            await self._session.rollback()
            persisted = await self._indexes.get(index.id)
            if persisted is not None:
                await self._indexes.mark_status(persisted, RetrievalIndexStatus.FAILED, str(exc))
                await self._session.commit()
                return persisted
            raise

    async def promote_index(self, index_id: int) -> RetrievalIndexVersion:
        """Promote a validated index by atomically switching its alias."""
        index = await self._require_index(index_id)
        if index.status not in {RetrievalIndexStatus.READY, RetrievalIndexStatus.ACTIVE}:
            raise EntityValidationError("Only validated indexes can be promoted")
        previous = await self._indexes.active_for_alias(index.alias_name)
        await self._deployment.promote(index.alias_name, index.collection_name)
        promoted = await self._indexes.promote(index, previous)
        await self._session.commit()
        return promoted

    async def rollback(self, alias_name: str) -> RetrievalIndexVersion:
        """Rollback the live alias to the previously retained production index."""
        previous = await self._indexes.previous_active_for_alias(alias_name)
        if previous is None:
            raise EntityNotFoundError("No previous index is available for rollback")
        active = await self._indexes.active_for_alias(alias_name)
        await self._deployment.rollback(alias_name, previous.collection_name)
        await self._indexes.promote(previous, active)
        await self._session.commit()
        return previous

    async def delete_index(self, index_id: int) -> None:
        """Delete a non-active index and its vector collection."""
        index = await self._require_index(index_id)
        if index.status == RetrievalIndexStatus.ACTIVE:
            raise EntityValidationError("Active indexes cannot be deleted")
        await self._vector_store.delete_collection(index.collection_name)
        await self._indexes.mark_status(index, RetrievalIndexStatus.DELETED)
        await self._session.commit()

    async def list_indexes(self) -> list[RetrievalIndexVersion]:
        """Return all known retrieval indexes."""
        return list(await self._indexes.list())

    async def status(self, alias_name: str) -> tuple[
        str | None,
        RetrievalIndexVersion | None,
        RetrievalIndexVersion | None,
        list[RetrievalIndexVersion],
    ]:
        """Return alias target, active index, rollback target, and history."""
        alias = await self._deployment.current(alias_name)
        active = await self._indexes.active_for_alias(alias_name)
        previous = await self._indexes.previous_active_for_alias(alias_name)
        indexes = list(await self._indexes.list())
        return alias.collection_name, active, previous, indexes

    async def _require_index(self, index_id: int) -> RetrievalIndexVersion:
        index = await self._indexes.get(index_id)
        if index is None:
            raise EntityNotFoundError("Retrieval index not found")
        return index

    async def _build_records(
        self,
        index: RetrievalIndexVersion,
        chunks: list[tuple[DocumentChunk, KnowledgeDocument]],
        build_mode: RetrievalBuildMode,
        alias_name: str,
    ) -> tuple[list[VectorRecord], list[IndexedDocumentState]]:
        grouped: dict[int, list[tuple[DocumentChunk, KnowledgeDocument]]] = defaultdict(list)
        for chunk, document in chunks:
            grouped[document.id].append((chunk, document))

        previous_state = await self._previous_document_state(alias_name)
        records: list[VectorRecord] = []
        states: list[IndexedDocumentState] = []
        now = datetime.now(UTC)

        for document_id, items in grouped.items():
            document = items[0][1]
            checksum = self._content_checksum([chunk.chunk_text for chunk, _ in items])
            previous = previous_state.get(document_id)
            unchanged = (
                previous is not None
                and previous.document_hash == document.file_hash
                and previous.content_checksum == checksum
                and previous.embedding_version == self._embedding_provider.model_version
            )
            if unchanged and build_mode in {RetrievalBuildMode.INCREMENTAL, RetrievalBuildMode.DELTA}:
                continue

            texts = [chunk.chunk_text for chunk, _ in items]
            vectors = await self._embedding_provider.embed_texts(texts)
            for (chunk, _), vector in zip(items, vectors, strict=True):
                records.append(
                    VectorRecord(
                        point_id=chunk.chunk_id,
                        vector=vector,
                        payload=self._payload(index, chunk, document, checksum, now),
                    )
                )
            states.append(
                IndexedDocumentState(
                    index_version_id=index.id,
                    document_id=document.id,
                    document_hash=document.file_hash,
                    content_checksum=checksum,
                    embedding_version=self._embedding_provider.model_version,
                    last_modified=document.updated_at,
                    last_indexed=now,
                    chunk_count=len(items),
                )
            )
        return records, states

    async def _previous_document_state(self, alias_name: str) -> dict[int, IndexedDocumentState]:
        active = await self._indexes.active_for_alias(alias_name)
        if active is None:
            return {}
        states = await self._indexes.states_for_index(active.id)
        return {state.document_id: state for state in states}

    def _payload(
        self,
        index: RetrievalIndexVersion,
        chunk: DocumentChunk,
        document: KnowledgeDocument,
        checksum: str,
        indexed_at: datetime,
    ) -> dict[str, str | int | float | bool | None]:
        metadata = dict(chunk.metadata_json or {})
        return {
            "document_id": document.id,
            "document_uuid": str(document.uuid),
            "title": document.title,
            "document_type": document.document_type,
            "document_hash": document.file_hash,
            "content_checksum": checksum,
            "chunk_id": str(chunk.chunk_id),
            "chunk_text": chunk.chunk_text,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "language": document.language,
            "crop": document.crop,
            "state": document.state,
            "district": document.district,
            "season": document.season,
            "authority": document.authority,
            "source": document.source,
            "source_url": document.source_url,
            "document_version": document.updated_at.isoformat(),
            "effective_from": metadata.get("effective_from"),
            "effective_until": metadata.get("effective_until"),
            "supersedes": metadata.get("supersedes"),
            "indexed_at": indexed_at.isoformat(),
            "collection": index.collection_name,
            "index_version": f"v{index.version_number:03d}",
        }

    @staticmethod
    def _content_checksum(texts: list[str]) -> str:
        digest = hashlib.sha256()
        for text in texts:
            digest.update(text.encode("utf-8"))
        return digest.hexdigest()
