"""Media API (F7): officers add and verify how-to content; farmers browse verified items.

Verification requires a recorded licence. When an item with a transcript is approved, the
transcript is ingested into the knowledge base (same parse -> chunk -> embed -> delta-index
path as uploaded documents), so the bot can cite it.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.catalog import get_crop_catalog
from app.config.settings import get_settings
from app.database.session import get_db_session
from app.media.service import to_card
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.models.media import MediaAsset

router = APIRouter(prefix="/media", tags=["Media (verified how-tos)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Curator = Annotated[AuthContext, Depends(RequirePermission(Permission.MEDIA_MANAGE))]
Viewer = Annotated[AuthContext, Depends(RequirePermission(Permission.CONVERSATION_USE))]


class MediaIn(BaseModel):
    kind: Literal["video", "howto"]
    title: str = Field(min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    url: HttpUrl
    source_org: str = Field(min_length=2, max_length=150, description="ICAR, KVK, SAU, state dept")
    licence: str | None = Field(default=None, max_length=150)
    licence_url: HttpUrl | None = None
    language: str = Field(pattern="^(en|hi|te)$")
    crops: list[str] = Field(default_factory=list, max_length=20)
    topics: list[str] = Field(min_length=1, max_length=20,
                              description="NLU intents/symptoms, e.g. disease, leaf_curl")
    duration_s: int | None = Field(default=None, ge=1, le=36000)
    transcript: str | None = Field(default=None, max_length=200_000)


class VerifyIn(BaseModel):
    approve: bool
    notes: str | None = Field(default=None, max_length=2000)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_media(body: MediaIn, session: DbSession, auth: Curator) -> dict:
    catalog = get_crop_catalog()
    unknown = [c for c in body.crops if c not in catalog]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"crops not in catalog: {unknown}")
    asset = MediaAsset(kind=body.kind, title=body.title, description=body.description,
                       url=str(body.url), source_org=body.source_org, licence=body.licence,
                       licence_url=str(body.licence_url) if body.licence_url else None,
                       language=body.language, crops=body.crops, topics=body.topics,
                       duration_s=body.duration_s, transcript=body.transcript,
                       added_by=auth.user_uuid)
    session.add(asset)
    await session.commit()
    return {"uuid": str(asset.uuid), "status": asset.status}


@router.post("/{media_uuid}/verify")
async def verify_media(media_uuid: UUID, body: VerifyIn, session: DbSession, auth: Curator,
                       background: BackgroundTasks) -> dict:
    asset = await session.scalar(select(MediaAsset).where(MediaAsset.uuid == media_uuid))
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media not found")
    if body.approve and not asset.licence:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Record the licence before approving (licence-checked content only)")
    asset.status = "verified" if body.approve else "rejected"
    asset.review_notes = body.notes
    asset.verified_by = auth.user_uuid
    asset.verified_at = datetime.now(UTC)
    if body.approve and asset.transcript and asset.knowledge_document_id is None:
        asset.knowledge_document_id = await _create_transcript_document(session, asset)
        background.add_task(_ingest, asset.knowledge_document_id)
    await session.commit()
    return {"uuid": str(asset.uuid), "status": asset.status,
            "knowledge_document_id": asset.knowledge_document_id}


@router.get("")
async def list_media(session: DbSession, auth: Viewer, crop: str | None = None,
                     topic: str | None = None, language: str | None = None) -> list[dict]:
    q = select(MediaAsset).where(MediaAsset.status == "verified")
    if language:
        q = q.where(MediaAsset.language == language)
    assets = (await session.scalars(q.order_by(MediaAsset.verified_at.desc()))).all()
    return [to_card(a) for a in assets
            if (crop is None or not a.crops or crop in a.crops)
            and (topic is None or topic in (a.topics or []))]


async def _create_transcript_document(session: AsyncSession, asset: MediaAsset) -> int:
    data = (asset.transcript or "").encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(get_settings().DOCUMENT_STORAGE_PATH) / "media_transcripts"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}.txt"
    path.write_bytes(data)
    doc = KnowledgeDocument(
        title=f"[Video transcript] {asset.title}", document_type="video_transcript",
        language=asset.language, source=asset.source_org, source_url=asset.url,
        authority=asset.source_org, crop=(asset.crops or [None])[0],
        uploaded_by=str(asset.verified_by), file_hash=digest, file_size=len(data),
        mime_type="text/plain", storage_path=str(path), status=DocumentStatus.PENDING)
    session.add(doc)
    await session.flush()
    return doc.id


async def _ingest(document_id: int) -> None:
    """Reuse the uploaded-document ingestion path (parse, chunk, embed, delta index)."""
    from app.api.routes.documents import (  # noqa: PLC0415
        _run_ingestion_background,
        get_embedding_pipeline,
        get_vector_store,
    )

    await _run_ingestion_background(document_id=document_id, vector_store=get_vector_store(),
                                    embedding_pipeline=get_embedding_pipeline())
