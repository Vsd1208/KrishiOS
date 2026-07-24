"""Semantic retrieval service.

Performs semantic search over embedded knowledge chunks using:
1. Embedding the user's query with the same model used at ingestion time.
2. Running a nearest-neighbour search in Qdrant with optional payload filters.
3. Enriching each hit with the full DocumentChunk and KnowledgeDocument
   records from PostgreSQL.

Architecture
------------
This service deliberately performs two lookups:
- Qdrant   → fast vector similarity ranking + metadata filters
- PostgreSQL → full chunk text + document metadata (source of truth)

The chunk_text is also stored in the Qdrant payload as a convenience cache
(avoiding a SQL round-trip for lightweight consumers). The SQL join is the
authoritative copy and is always returned in the SearchResponse.

No BM25 or hybrid reranking is implemented in Sprint 2. The architecture
is hybrid-ready: the retrieval service accepts a SearchFilter that could
be combined with a full-text match in a future sprint.
"""

from __future__ import annotations

import time

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embeddings.pipeline import EmbeddingPipeline
from app.knowledge.interfaces.vectorstore import SearchFilter
from app.knowledge.vectorstore.qdrant import QdrantVectorStore
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_document import KnowledgeDocument
from app.schemas.knowledge import (
    ChunkResponse,
    DocumentResponse,
    SearchFilters,
    SearchHit,
    SearchRequest,
    SearchResponse,
)


class RetrievalService:
    """Coordinates query embedding and Qdrant search.

    Parameters
    ----------
    session:
        SQLAlchemy async session for SQL lookups.
    vector_store:
        Qdrant client for vector search.
    embedding_pipeline:
        Same model used at ingestion time.
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_store: QdrantVectorStore,
        embedding_pipeline: EmbeddingPipeline,
    ) -> None:
        self._session = session
        self._vector_store = vector_store
        self._embedder = embedding_pipeline

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute semantic search and return enriched results.

        Parameters
        ----------
        request:
            Search request with query, filters, top_k, and threshold.

        Returns
        -------
        SearchResponse
            Ranked hits with chunk text, score, and document metadata.
        """
        t0 = time.perf_counter()

        # Step 1: Embed query
        query_vector = self._embedder.embed_query(request.query)

        # Step 2: Build Qdrant filter
        qdrant_filter = self._build_filter(request.filters)

        # Step 3: Vector search
        raw_hits = await self._vector_store.search(
            query_vector=query_vector,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            filters=qdrant_filter,
        )

        if not raw_hits:
            logger.info(
                "RetrievalService: no results for query='{}' threshold={}",
                request.query[:80],
                request.score_threshold,
            )
            return SearchResponse(
                query=request.query,
                top_k=request.top_k,
                total_hits=0,
                hits=[],
            )

        # Step 4: Enrich with PostgreSQL data
        hits = await self._enrich_hits(raw_hits)

        elapsed = time.perf_counter() - t0
        logger.info(
            "RetrievalService: search done query='{}' hits={} duration={:.3f}s",
            request.query[:80],
            len(hits),
            elapsed,
        )

        return SearchResponse(
            query=request.query,
            top_k=request.top_k,
            total_hits=len(hits),
            hits=hits,
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _enrich_hits(self, raw_hits: list) -> list[SearchHit]:
        """Fetch DocumentChunk + KnowledgeDocument rows and build SearchHit list."""
        from uuid import UUID

        # Collect all chunk UUIDs from Qdrant results
        chunk_uuids = [h.point_id for h in raw_hits]

        # Fetch chunks and eagerly load their documents
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.chunk_id.in_(chunk_uuids))
            .options()
        )
        chunk_rows: list[DocumentChunk] = list(result.scalars().all())

        # Build lookup: chunk_id → (chunk_row, document_row)
        chunk_map: dict[UUID, DocumentChunk] = {c.chunk_id: c for c in chunk_rows}
        doc_ids = list({c.document_id for c in chunk_rows})

        doc_result = await self._session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id.in_(doc_ids))
        )
        doc_rows: list[KnowledgeDocument] = list(doc_result.scalars().all())
        doc_map: dict[int, KnowledgeDocument] = {d.id: d for d in doc_rows}

        hits: list[SearchHit] = []
        for raw_hit in raw_hits:
            chunk_row = chunk_map.get(raw_hit.point_id)
            if chunk_row is None:
                logger.warning(
                    "RetrievalService: chunk_id={} found in Qdrant but not in PostgreSQL",
                    raw_hit.point_id,
                )
                continue

            doc_row = doc_map.get(chunk_row.document_id)
            if doc_row is None:
                logger.warning(
                    "RetrievalService: document_id={} not found in PostgreSQL",
                    chunk_row.document_id,
                )
                continue

            hits.append(
                SearchHit(
                    score=raw_hit.score,
                    page_number=chunk_row.page_number,
                    chunk=ChunkResponse.model_validate(chunk_row),
                    document=DocumentResponse.model_validate(doc_row),
                    metadata=chunk_row.metadata_json,
                )
            )

        # Preserve Qdrant's relevance ordering
        hit_order = {h.point_id: i for i, h in enumerate(raw_hits)}
        hits.sort(key=lambda h: hit_order.get(h.chunk.chunk_id, 999))
        return hits

    @staticmethod
    def _build_filter(filters: SearchFilters) -> SearchFilter | None:
        """Convert API SearchFilters into the internal SearchFilter dataclass."""
        if not any(
            [
                filters.language,
                filters.crop,
                filters.district,
                filters.state,
                filters.season,
                filters.authority,
                filters.document_id,
            ]
        ):
            return None

        return SearchFilter(
            language=filters.language,
            crop=filters.crop,
            district=filters.district,
            state=filters.state,
            season=filters.season,
            authority=filters.authority,
            document_id=filters.document_id,
        )
