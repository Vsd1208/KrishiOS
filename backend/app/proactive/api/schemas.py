"""Pydantic schemas for the Proactive Intelligence API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.proactive import (
    AlertPriority,
    AlertStatus,
    NotificationChannel,
    RiskSeverity,
)


class EventIngestRequest(BaseModel):
    """Payload to emit an internal or external agricultural event."""

    event_type: str = Field(..., description="Event type identifier, e.g. weather.alert")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload dictionary")
    source: str = Field("external_sync", description="Originating provider or subsystem")
    correlation_id: UUID | None = Field(None, description="Optional tracking correlation ID")


class EventIngestResponse(BaseModel):
    """Response returned upon event ingestion."""

    event_id: UUID
    status: str
    decisions_count: int
    message: str


class ProactiveDecisionResponse(BaseModel):
    """Summary of a proactive decision record."""

    decision_id: UUID
    event_id: UUID
    farmer_id: int | None
    field_id: int | None
    risk_type: str
    risk_severity: RiskSeverity
    confidence: float
    evidence_package: dict[str, Any]
    advisory_text: str
    requires_review: bool
    valid_until: datetime | None
    created_at: datetime


class AlertNotificationResponse(BaseModel):
    """Representation of an alert notification."""

    id: int
    uuid: UUID
    decision_id: int | None
    farmer_id: int
    channel: NotificationChannel
    title: str
    message: str
    priority: AlertPriority
    status: AlertStatus
    reviewed_by: UUID | None
    review_note: str | None
    sent_at: datetime | None
    acknowledged_at: datetime | None
    created_at: datetime


class OfficerReviewActionRequest(BaseModel):
    """Officer action for pending review items."""

    action: str = Field(..., description="'APPROVE' or 'REJECT'")
    review_note: str | None = Field(None, description="Optional officer notes")
    edited_message: str | None = Field(None, description="Optional modified advisory message before sending")


class NotificationPreferenceRequest(BaseModel):
    """Update farmer notification settings."""

    preferred_channel: NotificationChannel = NotificationChannel.IN_APP
    preferred_language: str = "te"
    min_severity: RiskSeverity = RiskSeverity.LOW
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "06:00"
    enable_weather_alerts: bool = True
    enable_disease_alerts: bool = True
    enable_market_alerts: bool = True
    enable_scheme_alerts: bool = True


class NotificationPreferenceResponse(NotificationPreferenceRequest):
    """Farmer notification preferences."""

    id: int
    farmer_id: int
    created_at: datetime
    updated_at: datetime
