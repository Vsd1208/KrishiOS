"""Full document ingestion pipeline.

Orchestrates the complete flow:
  Parse → Clean → Chunk → Embed → Store (PostgreSQL + Qdrant)

This module is the only entry point that combines all sub-systems.
It is called by FastAPI BackgroundTasks after a successful file upload.

Status machine
--------------
PENDING → PARSING → CHUNKING → EMBEDDING → COMPLETED
                                          ↘ FAILED

Each status transition is committed to PostgreSQL before the next stage
begins, so partial progress is visible via GET /documents/{id}.

Error handling
--------------
Any unhandled exception during processing transitions the document to
FAILED and records the error message. The pipeline does NOT retry
automatically — retries are a future enhancement via a task queue.

Logging
-------
Loguru is used at every stage with structured key/value pairs so logs
can be queried by document_id, stage, and duration.
"""

from __future__ import annotations

import time
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.chunking.pipeline import ChunkingPipeline
from app.knowledge.embeddings.pipeline import EmbeddingPipeline
from app.knowledge.ingestion.cleaning import TextCleaner
from app.knowledge.interfaces.chunker import ChunkerConfig
from app.knowledge.metadata.extractor import MetadataExtractor
from app.knowledge.parsers.selector import ParserSelector
from app.knowledge.vectorstore.qdrant import QdrantVectorStore
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument


class IngestionPipeline:
    """Orchestrates the full document ingestion lifecycle.

    Parameters
    ----------
    session:
        SQLAlchemy async session for status updates and chunk persistence.
    vector_store:
        Qdrant vector store instance for embedding storage.
    embedding_pipeline:
        Pre-loaded embedding pipeline (shared across requests).
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
        self._parser_selector = ParserSelector()
        self._cleaner = TextCleaner()
        self._chunker = ChunkingPipeline(
            config=ChunkerConfig(chunk_size=800, chunk_overlap=120)
        )
        self._meta_extractor = MetadataExtractor()

    # ── Public entry point ─────────────────────────────────────────────────

    async def run(self, document_id: int) -> None:
        """Run the full ingestion pipeline for a document.

        Reads file bytes from disk, processes through all stages, and
        persists results to PostgreSQL and Qdrant.

        This method is designed to be called from FastAPI BackgroundTasks.
        All exceptions are caught and recorded as FAILED status.
        """
        t_start = time.perf_counter()
        doc = await self._get_document(document_id)

        if doc is None:
            logger.error("IngestionPipeline: document_id={} not found", document_id)
            return

        logger.info(
            "IngestionPipeline: starting document_id={} title='{}'",
            document_id,
            doc.title,
        )

        try:
            await self._run_stages(doc)
            total = time.perf_counter() - t_start
            logger.info(
                "IngestionPipeline: COMPLETED document_id={} in {:.2f}s",
                document_id,
                total,
            )

        except Exception as exc:
            logger.exception(
                "IngestionPipeline: FAILED document_id={}: {}", document_id, exc
            )
            await self._set_status(doc, DocumentStatus.FAILED, error=str(exc))

    # ── Pipeline stages ────────────────────────────────────────────────────

    async def _run_stages(self, doc: KnowledgeDocument) -> None:
        """Execute all pipeline stages in order."""

        # ── Stage 1: Parse ────────────────────────────────────────────────
        await self._set_status(doc, DocumentStatus.PARSING)
        t0 = time.perf_counter()

        file_bytes = self._read_file(doc.storage_path)
        parsed, detected_mime = await self._parser_selector.parse(
            file_bytes, doc.title, mime_type=doc.mime_type
        )

        parse_duration = time.perf_counter() - t0
        logger.info(
            "IngestionPipeline: parse done document_id={} pages={} duration={:.3f}s",
            doc.id,
            parsed.total_pages,
            parse_duration,
        )

        # ── Metadata enrichment ────────────────────────────────────────────
        extracted = self._meta_extractor.extract(parsed.full_text)
        # Only fill gaps — user-provided metadata takes precedence.
        if not doc.language and extracted.detected_language:
            doc.language = extracted.detected_language
        if not doc.crop and extracted.detected_crop:
            doc.crop = extracted.detected_crop
        if not doc.season and extracted.detected_season:
            doc.season = extracted.detected_season
        await self._session.flush()

        # ── Stage 2: Chunk ────────────────────────────────────────────────
        await self._set_status(doc, DocumentStatus.CHUNKING)
        t0 = time.perf_counter()

        # Build per-chunk metadata from document fields.
        chunk_metadata: dict[str, str] = {}
        for key, value in {
            "language": doc.language,
            "crop": doc.crop,
            "district": doc.district,
            "state": doc.state,
            "season": doc.season,
            "authority": doc.authority,
        }.items():
            if value:
                chunk_metadata[key] = value

        chunks = self._chunker.run(
            parsed=parsed,
            document_type=doc.document_type,
            extra_metadata=chunk_metadata,
        )

        chunk_duration = time.perf_counter() - t0
        logger.info(
            "IngestionPipeline: chunked document_id={} chunks={} duration={:.3f}s",
            doc.id,
            len(chunks),
            chunk_duration,
        )

        # ── Stage 3: Embed ────────────────────────────────────────────────
        await self._set_status(doc, DocumentStatus.EMBEDDING)
        t0 = time.perf_counter()

        vector_points = self._embedder.embed_chunks(
            chunks=chunks,
            document_id=str(doc.id),
            document_uuid=str(doc.uuid),
            extra_payload={
                k: v
                for k, v in {
                    "language": doc.language or "en",
                    "crop": doc.crop or "",
                    "district": doc.district or "",
                    "state": doc.state or "",
                    "season": doc.season or "",
                    "authority": doc.authority or "",
                }.items()
            },
        )

        embed_duration = time.perf_counter() - t0
        logger.info(
            "IngestionPipeline: embedded document_id={} vectors={} duration={:.3f}s",
            doc.id,
            len(vector_points),
            embed_duration,
        )

        # ── Stage 4: Persist chunks to PostgreSQL ─────────────────────────
        db_chunks: list[DocumentChunk] = []
        for chunk, point in zip(chunks, vector_points, strict=True):
            db_chunk = DocumentChunk(
                chunk_id=point.point_id,
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                chunk_text=chunk.text,
                token_count=chunk.token_count,
                embedding_model=self._embedder.model_name,
                embedding_version=self._embedder.model_version,
                metadata_json=chunk.metadata or None,
            )
            db_chunks.append(db_chunk)

        self._session.add_all(db_chunks)
        await self._session.flush()

        # ── Stage 5: Upsert to Qdrant ──────────────────────────────────────
        await self._vector_store.upsert(vector_points)
        logger.info(
            "IngestionPipeline: vectors inserted document_id={} count={}",
            doc.id,
            len(vector_points),
        )

        # ── Stage 6: Graph Extraction ──────────────────────────────────────
        from app.graph.ingestion.graph_ingestion import GraphIngestionStage
        t0 = time.perf_counter()
        
        graph_stage = GraphIngestionStage(self._session)
        chunk_uuids = [point.point_id for point in vector_points]
        await graph_stage.run(doc=doc, chunks=chunks, chunk_uuids=chunk_uuids)
        
        graph_duration = time.perf_counter() - t0
        logger.info(
            "IngestionPipeline: graph extraction done document_id={} duration={:.3f}s",
            doc.id,
            graph_duration,
        )

        # ── Mark complete ──────────────────────────────────────────────────
        await self._set_status(doc, DocumentStatus.COMPLETED)
        await self._session.commit()

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _get_document(self, document_id: int) -> KnowledgeDocument | None:
        from sqlalchemy import select

        result = await self._session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def _set_status(
        self,
        doc: KnowledgeDocument,
        status: DocumentStatus,
        error: str | None = None,
    ) -> None:
        doc.status = status
        if error:
            doc.error_message = error[:2000]  # Prevent very long error messages
        await self._session.flush()
        logger.debug(
            "IngestionPipeline: status={} document_id={}", status.value, doc.id
        )

    @staticmethod
    def _read_file(storage_path: str) -> bytes:
        """Read file bytes from the storage path synchronously.

        File I/O here is synchronous because:
        1. The ingestion pipeline runs in a background task, not the event loop.
        2. aiofiles would require an extra await chain with no benefit here.
        """
        with open(storage_path, "rb") as fh:
            return fh.read()
