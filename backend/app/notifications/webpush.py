"""Web Push notifications (Phase 5).

With ``VAPID_PUBLIC_KEY`` / ``VAPID_PRIVATE_KEY`` / ``VAPID_SUBJECT`` configured, notifications are
sent to every browser the farmer subscribed (payloads encrypted to the browser's keys; the push
service only relays ciphertext). Without keys this provider is a sandbox: it records what it
would send. Subscriptions that the push service reports gone (404/410) are deleted.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.config.settings import get_settings
from app.models.proactive import NotificationChannel
from app.notifications.contracts import (
    BaseNotificationProvider,
    NotificationDeliveryResult,
    NotificationPayload,
)

GONE = {404, 410}
MAX_BODY = 300


def push_payload(payload: NotificationPayload) -> dict[str, Any]:
    body = (
        payload.message
        if len(payload.message) <= MAX_BODY
        else (payload.message[: MAX_BODY - 1] + "…")
    )
    return {
        "title": payload.title,
        "body": body,
        "lang": payload.language,
        "tag": payload.topic_key,
        "url": "/farmer/updates",
    }


class WebPushProvider(BaseNotificationProvider):
    def __init__(self) -> None:
        self.outbox: deque[dict[str, Any]] = deque(maxlen=200)

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    @staticmethod
    def configured() -> bool:
        s = get_settings()
        return bool(s.VAPID_PUBLIC_KEY and s.VAPID_PRIVATE_KEY and s.VAPID_SUBJECT)

    async def send(self, payload: NotificationPayload) -> NotificationDeliveryResult:
        data = push_payload(payload)
        if not self.configured():
            message_id = f"sandbox-push-{uuid.uuid4().hex[:12]}"
            self.outbox.append(
                {"message_id": message_id, "at": datetime.now(UTC).isoformat(), **data}
            )
            return NotificationDeliveryResult(
                success=True, channel=self.channel, message_id=message_id
            )
        sent = await self._send_real(payload.farmer_id, data)
        return NotificationDeliveryResult(
            success=sent > 0,
            channel=self.channel,
            message_id=f"webpush-{uuid.uuid4().hex[:12]}" if sent else None,
            error=None if sent else "no active push subscription",
        )

    async def _send_real(self, farmer_id: int, data: dict[str, Any]) -> int:
        from pywebpush import WebPushException, webpush  # noqa: PLC0415

        from app.database.session import async_session_factory  # noqa: PLC0415
        from app.models.govconnect import PushSubscription  # noqa: PLC0415

        s = get_settings()
        sent = 0
        async with async_session_factory() as session:
            subs = (
                await session.scalars(
                    select(PushSubscription).where(PushSubscription.farmer_id == farmer_id)
                )
            ).all()
            for sub in subs:
                info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
                try:
                    await asyncio.to_thread(
                        webpush,
                        subscription_info=info,
                        data=json.dumps(data),
                        vapid_private_key=s.VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": s.VAPID_SUBJECT},
                        ttl=6 * 3600,
                    )
                    sub.last_success_at, sub.failures = datetime.now(UTC), 0
                    sent += 1
                except WebPushException as exc:
                    status = getattr(exc.response, "status_code", None)
                    if status in GONE:
                        await session.delete(sub)
                    else:
                        sub.failures += 1
                    logger.warning("Web push failed ({})", status)
            await session.commit()
        return sent


_provider: WebPushProvider | None = None


def get_push_provider() -> WebPushProvider:
    global _provider  # noqa: PLW0603 - one outbox per process
    if _provider is None:
        _provider = WebPushProvider()
    return _provider
