"""SQLAlchemy ORM models for Sprint 10 Proactive Decision Intelligence."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.field import Field
    from app.models.user import User


class RiskSeverity(str, enum.Enum):
    """Severity levels for agricultural risk assessments."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    """Lifecycle states of an alert notification."""

    CREATED = "CREATED"
    EVALUATING = "EVALUATING"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class NotificationChannel(str, enum.Enum):
    """Communication channels for farmer notifications."""

    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    VOICE = "VOICE"


class AlertPriority(str, enum.Enum):
    """Urgency rating for alert dispatching."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ProactiveEventRecord(TimestampMixin, Base):
    """Persistent ledger of all received events and their idempotency status."""

    __tablename__ = "proactive_event_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="internal")
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED")

    __table_args__ = (
        Index("ix_proactive_event_type_status", "event_type", "status"),
    )


class ProactiveDecisionRecord(TimestampMixin, Base):
    """Immutable audit record of a proactive intelligence decision and evidence package."""

    __tablename__ = "proactive_decision_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    farmer_id: Mapped[int | None] = mapped_column(
        ForeignKey("farmer.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    field_id: Mapped[int | None] = mapped_column(
        ForeignKey("field.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    risk_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_severity: Mapped[RiskSeverity] = mapped_column(
        String(50),
        nullable=False,
        default=RiskSeverity.LOW,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_package: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    workflow_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    agent_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    advisory_text: Mapped[str] = mapped_column(Text, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    farmer: Mapped[Farmer | None] = relationship("Farmer")
    field: Mapped[Field | None] = relationship("Field")
    notifications: Mapped[list[AlertNotificationRecord]] = relationship(
        "AlertNotificationRecord", back_populates="decision"
    )

    __table_args__ = (
        Index("ix_proactive_decision_farmer_created", "farmer_id", "created_at"),
    )


class AlertNotificationRecord(TimestampMixin, Base):
    """An alert notification dispatched (or queued) for a farmer."""

    __tablename__ = "alert_notification_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    decision_id: Mapped[int | None] = mapped_column(
        ForeignKey("proactive_decision_record.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        String(50),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[AlertPriority] = mapped_column(
        String(50),
        nullable=False,
        default=AlertPriority.NORMAL,
    )
    status: Mapped[AlertStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AlertStatus.CREATED,
        index=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decision: Mapped[ProactiveDecisionRecord | None] = relationship(
        "ProactiveDecisionRecord", back_populates="notifications"
    )
    farmer: Mapped[Farmer] = relationship("Farmer")

    __table_args__ = (
        Index("ix_alert_notif_farmer_status", "farmer_id", "status"),
    )


class NotificationPreferenceRecord(TimestampMixin, Base):
    """Configurable notification preferences and quiet hours for a farmer."""

    __tablename__ = "notification_preference_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmer.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    preferred_channel: Mapped[NotificationChannel] = mapped_column(
        String(50),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )
    preferred_language: Mapped[str] = mapped_column(String(50), nullable=False, default="te")
    min_severity: Mapped[RiskSeverity] = mapped_column(
        String(50),
        nullable=False,
        default=RiskSeverity.LOW,
    )
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(10), nullable=False, default="22:00")
    quiet_hours_end: Mapped[str] = mapped_column(String(10), nullable=False, default="06:00")
    enable_weather_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_disease_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_market_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enable_scheme_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    farmer: Mapped[Farmer] = relationship("Farmer")
