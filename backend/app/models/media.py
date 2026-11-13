"""Verified how-to media (videos, illustrated steps) attachable to answers (Sprint 11, F7).

Only officer-verified items with a recorded licence are ever shown to farmers. Sources are
public extension content (ICAR, KVK, SAU, state agriculture departments).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_asset"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(default=uuid4, unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # video | howto
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_org: Mapped[str] = mapped_column(String(150), nullable=False)
    licence: Mapped[str | None] = mapped_column(String(150), nullable=True)
    licence_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    crops: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # catalog keys
    topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # intents/symptoms
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[UUID | None] = mapped_column(nullable=True)
    verified_by: Mapped[UUID | None] = mapped_column(nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    knowledge_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_media_asset_status", "status"),)
