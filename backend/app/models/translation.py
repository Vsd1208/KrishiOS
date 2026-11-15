"""Translation audit record: source, translation, provider/version, checks, approver."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class TranslationRecord(TimestampMixin, Base):
    """One translation of one text. Official content requires ``approved_by`` before delivery
    when its status is ``pending_review``."""

    __tablename__ = "translation_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(default=uuid4, unique=True, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_language: Mapped[str] = mapped_column(String(8), nullable=False)
    target_language: Mapped[str] = mapped_column(String(8), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    back_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    glossary_version: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by_reviewer: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        Index("ix_translation_record_hash", "content_hash"),
        Index("ix_translation_record_status", "status"),
    )
