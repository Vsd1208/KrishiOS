"""Index approved bulletins into RAG with validity metadata; expire them on withdraw/supersede.

The bulletin becomes a ``KnowledgeDocument`` (``document_type="govt_bulletin"``) whose chunks
carry ``effective_from`` / ``effective_until`` / ``bulletin_uuid``. Retrieval already drops
chunks past ``effective_until`` (``RetrievalPipeline._is_fresh``), so an expired bulletin is
never cited as current. Withdrawal sets ``effective_until`` to now in Postgres (kept by future
index rebuilds) and in the live + delta Qdrant payloads.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.govconnect import BulletinTranslation, GovtBulletin
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument


class BulletinIndexer(Protocol):
    async def index(self, document_id: int, metadata: dict[str, Any]) -> bool: ...

    async def expire(self, session: AsyncSession, document_id: int, when: datetime) -> bool: ...


def index_text(b: GovtBulletin, translations: list[BulletinTranslation]) -> str:
    """English first (the knowledge base is English), then the official original."""
    english = next((t for t in translations if t.language == "en"), None)
    header = (
        f"Official bulletin from {b.authority} ({b.authority_level}). "
        f"Issued: {b.issued_at.isoformat() if b.issued_at else 'unknown'}. "
        f"Valid until: {b.valid_to.isoformat() if b.valid_to else 'unknown'}."
    )
    parts = [header, b.title]
    if english and b.original_language != "en":
        parts += [english.title, english.body]
    parts.append(b.body)
    return "\n\n".join(p for p in parts if p)


async def prepare_document(
    session: AsyncSession, b: GovtBulletin, translations: list[BulletinTranslation]
) -> int:
    """Write the index text and a PENDING KnowledgeDocument (caller commits)."""
    from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415

    text = index_text(b, translations)
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(get_settings().DOCUMENT_STORAGE_PATH) / "govconnect"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{b.uuid}.txt"
    path.write_bytes(data)
    district = get_lgd_directory().district(b.district_codes[0]) if b.district_codes else None
    doc = KnowledgeDocument(
        title=f"[Govt bulletin] {b.title}"[:250],
        document_type="govt_bulletin",
        language="en" if any(t.language == "en" for t in translations) else b.original_language,
        source=b.source_name or b.authority,
        source_url=b.source_url,
        authority=b.authority,
        state=district.state_name if district else None,
        district=district.district_name if district else None,
        crop=(b.crops or [None])[0],
        uploaded_by=str(b.approved_by) if b.approved_by else None,
        file_hash=digest,
        file_size=len(data),
        mime_type="text/plain",
        storage_path=str(path),
        status=DocumentStatus.PENDING,
    )
    session.add(doc)
    await session.flush()
    return doc.id


def chunk_metadata(b: GovtBulletin, superseded_uuid: str | None) -> dict[str, Any]:
    return {
        "effective_from": (b.valid_from or b.issued_at).isoformat()
        if (b.valid_from or b.issued_at)
        else None,
        "effective_until": b.valid_to.isoformat() if b.valid_to else None,
        "supersedes": superseded_uuid,
        "bulletin_uuid": str(b.uuid),
        "authority_level": b.authority_level,
        "official": True,
    }


class QdrantBulletinIndexer:
    async def index(self, document_id: int, metadata: dict[str, Any]) -> bool:
        from app.api.routes.documents import (  # noqa: PLC0415
            _run_ingestion_background,
            get_embedding_pipeline,
            get_vector_store,
        )

        return bool(
            await _run_ingestion_background(
                document_id=document_id,
                vector_store=get_vector_store(),
                embedding_pipeline=get_embedding_pipeline(),
                chunk_metadata=metadata,
            )
        )

    async def expire(self, session: AsyncSession, document_id: int, when: datetime) -> bool:
        from app.models.document_chunk import DocumentChunk  # noqa: PLC0415
        from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore  # noqa: PLC0415

        rows = (
            await session.scalars(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
        ).all()
        for row in rows:
            row.metadata_json = {**(row.metadata_json or {}), "effective_until": when.isoformat()}
        await session.flush()
        settings = get_settings()
        try:
            store = QdrantRetrievalVectorStore(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            payload = {"effective_until": when.isoformat()}
            for alias in (settings.RETRIEVAL_LIVE_ALIAS, settings.RETRIEVAL_DELTA_ALIAS):
                await store.set_document_payload(alias, document_id, payload)
        except Exception as exc:  # the maintenance job retries
            logger.warning("Bulletin index expiry failed for document {}: {}", document_id, exc)
            return False
        return True


_indexer: BulletinIndexer | None = None


def get_indexer() -> BulletinIndexer:
    global _indexer  # noqa: PLW0603 - process-wide default, replaceable in tests
    if _indexer is None:
        _indexer = QdrantBulletinIndexer()
    return _indexer


def set_indexer(indexer: BulletinIndexer | None) -> None:
    global _indexer  # noqa: PLW0603
    _indexer = indexer
