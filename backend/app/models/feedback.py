"""Feedback on bot answers, government bulletins and photo diagnoses (Sprint 11, F13)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class AnswerFeedback(TimestampMixin, Base):
    __tablename__ = "answer_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(default=uuid4, unique=True, nullable=False)
    # answer | bulletin | diagnosis
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_uuid: Mapped[UUID] = mapped_column(nullable=False)
    rating: Mapped[str] = mapped_column(String(8), nullable=False)  # up | down
    useful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(24), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="new")
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_answer_feedback_target", "target_type", "target_id"),
        Index("ix_answer_feedback_status", "status", "rating"),
    )
