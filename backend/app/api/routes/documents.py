"""REST API routes for the Knowledge Infrastructure.

Endpoints
---------
POST   /documents/upload   — Upload a document and start background ingestion
GET    /documents          — List all documents with pagination
GET    /documents/{id}     — Get document detail and ingestion status
DELETE /documents/{id}     — Soft-delete document and remove from Qdrant
POST   /documents/search   — Semantic search over embedded chunks

Design rules (Clean Architecture)
----------------------------------
* No business logic in this module. All orchestration happens in services.
* Dependency injection via FastAPI Depends for all stateful services.
* File size and MIME validation happens here before any I/O.
* Background ingestion is triggered via FastAPI BackgroundTasks after the
  upload response is already returned (202 Accepted pattern).
* Newly uploaded documents are synchronized into the production retrieval
  delta index after canonical ingestion succeeds.
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_db_session
from app.knowledge.embeddings.pipeline import EmbeddingPipeline
from app.knowledge.pipelines.ingestion_pipeline import IngestionPipeline
from app.knowledge.retrieval.service import RetrievalService
from app.knowledge.storage.file_store import FileStore
from app.knowledge.vectorstore.qdrant import QdrantVectorStore
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.retrieval.ingestion.incremental import IncrementalIngestionService
from app.retrieval.providers.embeddings import (
    SentenceTransformerEmbeddingProvider,
)
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore
from app.schemas.knowledge import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadMetadata,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/documents", tags=["Knowledge"])


# ── Dependency factories ──────────────────────────────────────────────────────


def get_vector_store() -> QdrantVectorStore:
    """Build the existing document-management Qdrant vector store.

    This dependency is retained for the existing document search and delete
    endpoints. Upload synchronization into the production retrieval index is
    handled separately by IncrementalIngestionService.
    """
    settings = get_settings()

    return QdrantVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        collection_name=settings.QDRANT_COLLECTION,
    )


def get_embedding_pipeline() -> EmbeddingPipeline:
    """Return the existing knowledge embedding pipeline."""
    settings = get_settings()

    return EmbeddingPipeline(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_version=settings.EMBEDDING_MODEL_VERSION,
    )


def get_file_store() -> FileStore:
    """Return the file storage service."""
    settings = get_settings()

    return FileStore(
        base_dir=settings.DOCUMENT_STORAGE_PATH,
    )


# ── Convenience type aliases ──────────────────────────────────────────────────

DbSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

VectorStoreDep = Annotated[
    QdrantVectorStore,
    Depends(get_vector_store),
]

EmbedderDep = Annotated[
    EmbeddingPipeline,
    Depends(get_embedding_pipeline),
]

FileStoreDep = Annotated[
    FileStore,
    Depends(get_file_store),
]


# ── Allowed MIME types ─────────────────────────────────────────────────────────

_ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
    "image/bmp",
}


# ── Upload ────────────────────────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for ingestion",
    description=(
        "Accepts PDF, DOCX, TXT, or image files up to the configured max size. "
        "Duplicate detection is performed via SHA-256 hash. "
        "Ingestion runs asynchronously — poll GET /documents/{id} for status."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    session: DbSession,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    file_store: FileStoreDep,
    file: Annotated[
        UploadFile,
        File(description="Document to ingest"),
    ],
    metadata: Annotated[
        str,
        Form(description="JSON-encoded DocumentUploadMetadata"),
    ] = "{}",
) -> DocumentUploadResponse:
    """Upload a document and trigger asynchronous ingestion."""

    settings = get_settings()

    # ── Parse metadata ────────────────────────────────────────────────────────
    try:
        meta_dict = json.loads(metadata)
        doc_meta = DocumentUploadMetadata(**meta_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata JSON: {exc}",
        ) from exc

    # ── Read file ─────────────────────────────────────────────────────────────
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # ── Validate file size ────────────────────────────────────────────────────
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds maximum size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB"
            ),
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # ── Validate MIME type ────────────────────────────────────────────────────
    content_type = file.content_type or ""
    detected_mime = content_type.split(";")[0].strip()

    if detected_mime not in _ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{detected_mime}'. "
                f"Allowed: {sorted(_ALLOWED_MIMES)}"
            ),
        )

    # ── Duplicate detection ──────────────────────────────────────────────────
    file_hash = FileStore.compute_hash(file_bytes)

    existing = await session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.file_hash == file_hash
        )
    )

    duplicate = existing.scalar_one_or_none()

    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Duplicate document. Already ingested as "
                f"document_id={duplicate.id} "
                f"(status={duplicate.status.value})"
            ),
        )

    # ── Persist file ──────────────────────────────────────────────────────────
    filename = file.filename or "upload"

    storage_path = await file_store.save(
        file_bytes,
        file_hash,
        filename,
    )

    # ── Create database document ──────────────────────────────────────────────
    doc = KnowledgeDocument(
        title=doc_meta.title,
        document_type=doc_meta.document_type,
        language=doc_meta.language,
        source=doc_meta.source,
        source_url=(
            str(doc_meta.source_url)
            if doc_meta.source_url
            else None
        ),
        authority=doc_meta.authority,
        state=doc_meta.state,
        district=doc_meta.district,
        crop=doc_meta.crop,
        season=doc_meta.season,
        uploaded_by=doc_meta.uploaded_by,
        file_hash=file_hash,
        file_size=file_size,
        mime_type=detected_mime,
        storage_path=str(storage_path),
        status=DocumentStatus.PENDING,
    )

    session.add(doc)

    await session.commit()
    await session.refresh(doc)

    logger.info(
        "upload: document_id={} title='{}' size_bytes={} mime={}",
        doc.id,
        doc.title,
        file_size,
        detected_mime,
    )

    # ── Schedule asynchronous ingestion ───────────────────────────────────────
    background_tasks.add_task(
        _run_ingestion_background,
        document_id=doc.id,
        vector_store=vector_store,
        embedding_pipeline=embedder,
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        uuid=doc.uuid,
        title=doc.title,
        status=doc.status.value,
    )


# ── Background ingestion ──────────────────────────────────────────────────────


async def _run_ingestion_background(
    document_id: int,
    vector_store: QdrantVectorStore,
    embedding_pipeline: EmbeddingPipeline,
) -> None:
    """Run canonical ingestion followed by production delta indexing.

    Flow
    ----
    1. Parse uploaded document.
    2. Extract/resolve metadata.
    3. Create DocumentChunk records in PostgreSQL.
    4. Complete canonical document ingestion.
    5. Build production retrieval embedding provider.
    6. Index this document into the active retrieval delta collection.

    The production live alias is never modified here. New documents go to
    krishios-delta and are picked up by the enterprise retrieval pipeline,
    which searches both krishios-live and krishios-delta.
    """

    from app.database.session import async_session_factory

    settings = get_settings()

    async with async_session_factory() as session:
        try:
            # ─────────────────────────────────────────────────────────────
            # Stage 1: Canonical document ingestion
            # ─────────────────────────────────────────────────────────────
            pipeline = IngestionPipeline(
                session=session,
                vector_store=vector_store,
                embedding_pipeline=embedding_pipeline,
            )

            await pipeline.run(document_id)

            # ─────────────────────────────────────────────────────────────
            # Stage 2: Confirm canonical ingestion succeeded
            # ─────────────────────────────────────────────────────────────
            result = await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.id == document_id
                )
            )

            document = result.scalar_one_or_none()

            if document is None:
                logger.error(
                    "Background ingestion: document_id={} "
                    "not found after canonical ingestion",
                    document_id,
                )
                return

            if document.status != DocumentStatus.COMPLETED:
                logger.warning(
                    "Background ingestion: document_id={} "
                    "canonical ingestion ended with status={}; "
                    "production retrieval indexing skipped",
                    document_id,
                    document.status.value,
                )
                return

            # ─────────────────────────────────────────────────────────────
            # Stage 3: Production retrieval providers
            # ─────────────────────────────────────────────────────────────
            #
            # IMPORTANT:
            # Do not use QDRANT_COLLECTION here.
            #
            # QdrantRetrievalVectorStore intentionally operates with the
            # versioned retrieval collections and aliases:
            #
            #   krishios-live
            #   krishios-delta
            #
            # This keeps document upload decoupled from the active
            # blue/green production index.
            retrieval_vector_store = QdrantRetrievalVectorStore(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            retrieval_embedding_provider = (
                SentenceTransformerEmbeddingProvider(
                    model_name=settings.EMBEDDING_MODEL_NAME,
                    model_version=settings.EMBEDDING_MODEL_VERSION,
                )
            )

            # ─────────────────────────────────────────────────────────────
            # Stage 4: Incremental production indexing
            # ─────────────────────────────────────────────────────────────
            incremental_service = IncrementalIngestionService(
                session=session,
                vector_store=retrieval_vector_store,
                embedding_provider=retrieval_embedding_provider,
                delta_alias=settings.RETRIEVAL_DELTA_ALIAS,
            )

            indexed_count = await incremental_service.ingest_to_delta(
                document_id=document_id,
                alias_name=settings.RETRIEVAL_LIVE_ALIAS,
            )

            await session.commit()

            logger.info(
                "Background ingestion: document_id={} "
                "successfully synchronized to retrieval delta; "
                "vectors={} delta_alias={} live_alias={}",
                document_id,
                indexed_count,
                settings.RETRIEVAL_DELTA_ALIAS,
                settings.RETRIEVAL_LIVE_ALIAS,
            )

        except Exception as exc:
            logger.exception(
                "Background ingestion failed for document_id={}: {}",
                document_id,
                exc,
            )

            await session.rollback()

            # Record failure status in a clean transaction.
            try:
                result = await session.execute(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.id == document_id
                    )
                )

                document = result.scalar_one_or_none()

                if document is not None:
                    document.status = DocumentStatus.FAILED
                    await session.commit()

            except Exception:
                logger.exception(
                    "Background ingestion: failed to record FAILED "
                    "status for document_id={}",
                    document_id,
                )


# ── List documents ────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all ingested documents",
)
async def list_documents(
    session: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    crop: str | None = None,
    language: str | None = None,
) -> DocumentListResponse:
    """Return paginated list of documents with optional filters."""

    stmt = select(KnowledgeDocument)

    if status_filter:
        try:
            document_status = DocumentStatus(status_filter)
            stmt = stmt.where(
                KnowledgeDocument.status == document_status
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter '{status_filter}'",
            ) from None

    if crop:
        stmt = stmt.where(
            KnowledgeDocument.crop.ilike(f"%{crop}%")
        )

    if language:
        stmt = stmt.where(
            KnowledgeDocument.language == language
        )

    total_result = await session.execute(
        select(func.count()).select_from(stmt.subquery())
    )

    total = total_result.scalar_one()

    items_result = await session.execute(
        stmt.offset(offset).limit(limit)
    )

    items = list(items_result.scalars().all())

    return DocumentListResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[
            DocumentResponse.model_validate(document)
            for document in items
        ],
    )


# ── Get document ──────────────────────────────────────────────────────────────


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata and status",
)
async def get_document(
    document_id: int,
    session: DbSession,
) -> DocumentResponse:
    """Return metadata and current ingestion status."""

    result = await session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id
        )
    )

    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return DocumentResponse.model_validate(doc)


# ── Delete document ───────────────────────────────────────────────────────────


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and remove its vectors",
)
async def delete_document(
    document_id: int,
    session: DbSession,
    vector_store: VectorStoreDep,
    file_store: FileStoreDep,
) -> Response:
    """Delete a document and remove its legacy document vectors.

    PostgreSQL cascade removes DocumentChunk rows.
    The existing document Qdrant collection is cleaned using the document UUID.
    """

    result = await session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id
        )
    )

    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Remove vectors from the existing document-management collection.
    try:
        await vector_store.delete_by_document(str(doc.uuid))
    except Exception as exc:
        logger.warning(
            "delete_document: legacy Qdrant deletion failed "
            "for document_uuid={}: {}",
            doc.uuid,
            exc,
        )

    # Remove physical file.
    await file_store.delete(doc.storage_path)

    # Remove PostgreSQL document.
    await session.delete(doc)
    await session.commit()

    logger.info(
        "delete_document: removed document_id={}",
        document_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Semantic search ───────────────────────────────────────────────────────────


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over document chunks",
    description=(
        "Embeds the query using the same model used at ingestion time, "
        "then searches Qdrant for the most relevant chunks. "
        "No LLM is involved — this returns raw chunks with scores, "
        "not generated answers."
    ),
)
async def search_documents(
    request: SearchRequest,
    session: DbSession,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
) -> SearchResponse:
    """Run semantic search and return ranked chunks with metadata."""

    retrieval_service = RetrievalService(
        session=session,
        vector_store=vector_store,
        embedding_pipeline=embedder,
    )

    return await retrieval_service.search(request)