"""Extension-worker assignments with recorded farmer consent (Sprint 11, F6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class ExtensionAssignment(TimestampMixin, Base):
    """A worker may act for a farmer only while the assignment is active and consent is
    ``granted``. Consent is recorded with its method and evidence and can be revoked."""

    __tablename__ = "extension_assignment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    worker_user_uuid: Mapped[UUID] = mapped_column(nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmer.id", ondelete="CASCADE"),
                                           nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    consent_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    consent_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                                 nullable=True)
    assigned_by: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("worker_user_uuid", "farmer_id", name="uq_extension_worker_farmer"),
        Index("ix_extension_assignment_worker", "worker_user_uuid", "active"),
    )
