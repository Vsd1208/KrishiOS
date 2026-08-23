"""Concrete Notification Providers for KrishiOS."""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from app.models.proactive import NotificationChannel
from app.notifications.contracts import (
    BaseNotificationProvider,
    NotificationDeliveryResult,
    NotificationPayload,
)


class InMemoryNotificationProvider(BaseNotificationProvider):
    """In-memory notification provider tracking delivered payloads for automated testing."""

    def __init__(self, channel: NotificationChannel = NotificationChannel.IN_APP) -> None:
        self._channel = channel
        self.sent_notifications: list[NotificationPayload] = []

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        self.sent_notifications.append(payload)
        logger.info(
            "InMemoryProvider: delivered {} notification to farmer_id={} title='{}'",
            self._channel.value,
            payload.farmer_id,
            payload.title,
        )
        return NotificationDeliveryResult(
            success=True,
            channel=self._channel,
            message_id=f"mem-{uuid.uuid4()}",
        )

    def clear(self) -> None:
        """Clear sent history."""
        self.sent_notifications.clear()


class ConsoleNotificationProvider(BaseNotificationProvider):
    """Logs notifications directly to stdout/loguru for development."""

    def __init__(self, channel: NotificationChannel = NotificationChannel.IN_APP) -> None:
        self._channel = channel

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        logger.info(
            "\n" + "=" * 60 + "\n"
            f"[NOTIFICATION - {self._channel.value.upper()}] To Farmer ID: {payload.farmer_id}\n"
            f"Title: {payload.title}\n"
            f"Language: {payload.language} | Priority: {payload.priority.value}\n"
            f"Message:\n{payload.message}\n"
            + "=" * 60
        )
        return NotificationDeliveryResult(
            success=True,
            channel=self._channel,
            message_id=f"console-{uuid.uuid4()}",
        )


class MockSMSNotificationProvider(BaseNotificationProvider):
    """Simulates telecom SMS gateway integration (e.g. CDAC / Twilio / MSG91)."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS

    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        # Simulate character limit validation
        sms_text = payload.message[:160] if len(payload.message) > 160 else payload.message
        logger.info(
            "MockSMSProvider: SMS sent to farmer_id={} length={} chars: '{}'",
            payload.farmer_id,
            len(sms_text),
            sms_text[:50] + "...",
        )
        return NotificationDeliveryResult(
            success=True,
            channel=NotificationChannel.SMS,
            message_id=f"sms-{uuid.uuid4()}",
        )
