"""Incremental change detection and delta collection indexing manager."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.retrieval_index import IndexedDocumentState
from app.retrieval.indexing.repository import (
    RetrievalDocumentRepository,
    RetrievalIndexRepository,
)
from app.retrieval.interfaces.providers import EmbeddingProvider, VectorStoreProvider
from app.retrieval.interfaces.types import VectorRecord


class IncrementalIngestionService:
    """Manages incremental document change detection and delta collection updates."""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: VectorStoreProvider,
        embedding_provider: EmbeddingProvider,
        delta_alias: str = "krishios-delta",
    ) -> None:
        self._session = session
        self._documents = RetrievalDocumentRepository(session)
        self._indexes = RetrievalIndexRepository(session)
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._delta_alias = delta_alias

    async def inspect_document_change(
        self,
        document_id: int,
        alias_name: str = "krishios-live",
    ) -> bool:
        """Return True if a document needs re-indexing (hash/content/model changed)."""
        active_index = await self._indexes.active_for_alias(alias_name)
        if active_index is None:
            return True

        states = await self._indexes.states_for_index(active_index.id)
        state_map = {state.document_id: state for state in states}
        previous = state_map.get(document_id)
        if previous is None:
            return True

        doc = await self._documents.get_by_id(document_id)
        if doc is None:
            return False

        chunks = await self._documents.load_chunks_for_document(document_id)
        checksum = self.compute_checksum([chunk.chunk_text for chunk in chunks])

        return not (
            previous.document_hash == doc.file_hash
            and previous.content_checksum == checksum
            and previous.embedding_version == self._embedding_provider.model_version
        )

    async def ingest_to_delta(
        self,
        document_id: int,
        alias_name: str = "krishios-live",
    ) -> int:
        """Index a single document directly into the active delta collection.

        Returns the number of vector records written to the delta index.
        """
        needs_update = await self.inspect_document_change(document_id, alias_name)
        if not needs_update:
            return 0

        doc = await self._documents.get_by_id(document_id)
        if doc is None:
            return 0

        chunks = await self._documents.load_chunks_for_document(document_id)
        if not chunks:
            return 0

        checksum = self.compute_checksum([chunk.chunk_text for chunk in chunks])
        now = datetime.now(UTC)

        delta_state = await self._vector_store.get_alias_state(self._delta_alias)
        delta_collection = delta_state.collection_name
        if delta_collection is None:
            delta_collection = f"{self._delta_alias}-collection"
            await self._vector_store.create_collection(
                delta_collection,
                self._embedding_provider.vector_size,
            )
            await self._vector_store.switch_alias(self._delta_alias, delta_collection)

        texts = [chunk.chunk_text for chunk in chunks]
        vectors = await self._embedding_provider.embed_texts(texts)

        records: list[VectorRecord] = [
            VectorRecord(
                point_id=chunk.chunk_id,
                vector=vector,
                payload=self._build_payload(chunk, doc, checksum, now, delta_collection),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

        await self._vector_store.upsert(delta_collection, records)
        return len(records)

    @staticmethod
    def compute_checksum(texts: list[str]) -> str:
        """Compute SHA-256 digest of document chunk text content."""
        digest = hashlib.sha256()
        for text in texts:
            digest.update(text.encode("utf-8"))
        return digest.hexdigest()

    def _build_payload(
        self,
        chunk: DocumentChunk,
        document: KnowledgeDocument,
        checksum: str,
        indexed_at: datetime,
        collection_name: str,
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
            "collection": collection_name,
            "index_version": "delta",
        }
