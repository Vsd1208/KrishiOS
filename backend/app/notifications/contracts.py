"""Data contracts and provider interfaces for the Notification Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.models.proactive import AlertPriority, NotificationChannel


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    """Standardized payload for dispatching an alert notification."""

    farmer_id: int
    title: str
    message: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: AlertPriority = AlertPriority.NORMAL
    language: str = "te"
    topic_key: str = "general"
    decision_id: int | None = None
    notification_uuid: UUID = field(default_factory=uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NotificationDeliveryResult:
    """Result of a notification delivery attempt."""

    success: bool
    channel: NotificationChannel
    message_id: str | None = None
    error: str | None = None
    suppressed: bool = False
    suppression_reason: str | None = None
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class BaseNotificationProvider(ABC):
    """Abstract interface for multi-channel notification providers."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """The communication channel this provider serves."""

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        """Send the notification via the underlying communication carrier."""
