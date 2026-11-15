"""Conversation turn audit record (Sprint 11, Phase 3).

One row per bot turn: what was asked, in which language, what was answered, the providers
used and whether the turn needs officer review. Feedback (F13) references ``turn_uuid``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class ConversationTurnRecord(TimestampMixin, Base):
    __tablename__ = "conversation_turn"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turn_uuid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(32), nullable=False)
    user_uuid: Mapped[UUID] = mapped_column(nullable=False)
    acting_for_farmer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    # Set when the farmer used "ask about this" on a Govt Connect bulletin (Phase 4).
    bulletin_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    detected_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    user_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reply_text: Mapped[str] = mapped_column(Text, nullable=False)
    reply_text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    slots: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    providers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    translation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    shared_with_farmer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_conversation_turn_conversation", "conversation_id"),
        Index("ix_conversation_turn_review", "requires_review"),
    )
