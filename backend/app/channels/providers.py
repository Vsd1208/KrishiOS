"""Channel adapters (F5): SMS, voice (IVR) and WhatsApp behind ``BaseNotificationProvider``.

Only sandbox adapters exist: they compose exactly what would be sent (segments, encoding,
call script) and keep it in an outbox for inspection, but nothing leaves KrishiOS. A real
provider (an SMS/IVR aggregator, WhatsApp Business) needs a contract and cost approval
(Phase 0 decision) and plugs in behind the same interface, selected by ``*_PROVIDER``.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.channels.messages import alert_call, compose_sms
from app.models.proactive import NotificationChannel
from app.notifications.contracts import (
    BaseNotificationProvider,
    NotificationDeliveryResult,
    NotificationPayload,
)
from app.providers import ProviderInfo, ProviderKind, ProviderSelector

OUTBOX_SIZE = 500


def mask(identifier: str | int) -> str:
    """Stable pseudonym for logs/outbox: never store a phone number in the sandbox outbox."""
    return "f-" + hashlib.sha256(str(identifier).encode()).hexdigest()[:10]


class SandboxChannelProvider(BaseNotificationProvider):
    def __init__(self, channel: NotificationChannel) -> None:
        self._channel = channel
        self.outbox: deque[dict[str, Any]] = deque(maxlen=OUTBOX_SIZE)

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    def render(self, payload: NotificationPayload) -> dict[str, Any]:
        language = payload.language if payload.language in {"en", "hi", "te"} else "en"
        if self._channel == NotificationChannel.SMS:
            sms = compose_sms(f"{payload.title}\n{payload.message}", language)
            return {
                "text": sms.text,
                "encoding": sms.encoding,
                "segments": sms.segments,
                "truncated": sms.truncated,
            }
        if self._channel == NotificationChannel.VOICE:
            authority, _, title = payload.title.partition(": ")
            return {
                "call_script": alert_call(
                    title or authority,
                    payload.message,
                    authority if title else "KrishiOS",
                    language,
                ).to_dict()
            }
        return {"text": f"*{payload.title}*\n{payload.message}"}  # WhatsApp markdown

    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        message_id = f"sandbox-{self._channel.value.lower()}-{uuid.uuid4().hex[:12]}"
        self.outbox.append(
            {
                "message_id": message_id,
                "channel": self._channel.value,
                "to": mask(payload.farmer_id),
                "language": payload.language,
                "topic": payload.topic_key,
                "at": datetime.now(UTC).isoformat(),
                **self.render(payload),
            }
        )
        logger.info("Sandbox {} message {} (not sent)", self._channel.value, message_id)
        return NotificationDeliveryResult(
            success=True, channel=self._channel, message_id=message_id
        )


sms_selector: ProviderSelector[BaseNotificationProvider] = ProviderSelector("sms")
voice_selector: ProviderSelector[BaseNotificationProvider] = ProviderSelector("voice")
whatsapp_selector: ProviderSelector[BaseNotificationProvider] = ProviderSelector("whatsapp")

for _sel, _channel in (
    (sms_selector, NotificationChannel.SMS),
    (voice_selector, NotificationChannel.VOICE),
    (whatsapp_selector, NotificationChannel.WHATSAPP),
):
    _sel.register(
        ProviderInfo(
            _sel.capability,
            "sandbox",
            "1.0.0",
            ProviderKind.SANDBOX,
            description=f"Composes {_channel.value} messages into an outbox; "
            "nothing is sent. Real provider pending approval.",
        ),
        lambda c=_channel: SandboxChannelProvider(c),
    )


def _register_status() -> None:
    from app.providers.status import register_capability  # noqa: PLC0415

    register_capability("sms", lambda s: s.SMS_PROVIDER, lambda: sms_selector)
    register_capability("voice", lambda s: s.VOICE_PROVIDER, lambda: voice_selector)
    register_capability("whatsapp", lambda s: s.WHATSAPP_PROVIDER, lambda: whatsapp_selector)


_register_status()


def channel_providers() -> dict[NotificationChannel, BaseNotificationProvider]:
    from app.config.settings import get_settings  # noqa: PLC0415

    s = get_settings()
    return {
        NotificationChannel.SMS: sms_selector.get(s.SMS_PROVIDER),
        NotificationChannel.VOICE: voice_selector.get(s.VOICE_PROVIDER),
        NotificationChannel.WHATSAPP: whatsapp_selector.get(s.WHATSAPP_PROVIDER),
    }
