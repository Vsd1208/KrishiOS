"""Notification Service orchestrating farmer preferences, deduplication, and multi-channel delivery."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proactive import (
    AlertNotificationRecord,
    AlertPriority,
    AlertStatus,
    NotificationChannel,
    NotificationPreferenceRecord,
    RiskSeverity,
)
from app.notifications.contracts import (
    BaseNotificationProvider,
    NotificationDeliveryResult,
    NotificationPayload,
)
from app.notifications.providers import InMemoryNotificationProvider
from app.proactive.deduplication import EventDeduplicator


class NotificationService:
    """Enterprise Notification Service for KrishiOS farmers."""

    def __init__(
        self,
        deduplicator: EventDeduplicator | None = None,
        providers: dict[NotificationChannel, BaseNotificationProvider] | None = None,
    ) -> None:
        self._deduplicator = deduplicator or EventDeduplicator()
        self._providers = providers or {
            NotificationChannel.IN_APP: InMemoryNotificationProvider(NotificationChannel.IN_APP),
            NotificationChannel.SMS: InMemoryNotificationProvider(NotificationChannel.SMS),
            NotificationChannel.PUSH: InMemoryNotificationProvider(NotificationChannel.PUSH),
            NotificationChannel.VOICE: InMemoryNotificationProvider(NotificationChannel.VOICE),
        }

    def register_provider(self, provider: BaseNotificationProvider) -> None:
        """Register a channel provider."""
        self._providers[provider.channel] = provider

    async def dispatch_alert(
        self,
        session: AsyncSession,
        farmer_id: int,
        title: str,
        message: str,
        alert_type: str,
        topic_key: str,
        severity: RiskSeverity = RiskSeverity.LOW,
        priority: AlertPriority = AlertPriority.NORMAL,
        decision_id: int | None = None,
        requires_review: bool = False,
    ) -> AlertNotificationRecord:
        """Evaluate preferences, deduplicate, and dispatch or queue alert notification."""
        # 1. Fetch farmer preferences
        pref = await self._get_or_create_preferences(session, farmer_id)

        # 2. Check category toggles
        if alert_type.startswith("weather") and not pref.enable_weather_alerts:
            logger.info("NotificationService: weather alerts disabled for farmer_id={}", farmer_id)
            return await self._create_suppressed_record(
                session, farmer_id, title, message, priority, "Category 'weather' disabled by user"
            )
        if alert_type.startswith("agronomy") and not pref.enable_disease_alerts:
            logger.info("NotificationService: disease alerts disabled for farmer_id={}", farmer_id)
            return await self._create_suppressed_record(
                session, farmer_id, title, message, priority, "Category 'disease' disabled by user"
            )
        if alert_type.startswith("market") and not pref.enable_market_alerts:
            logger.info("NotificationService: market alerts disabled for farmer_id={}", farmer_id)
            return await self._create_suppressed_record(
                session, farmer_id, title, message, priority, "Category 'market' disabled by user"
            )
        if alert_type.startswith("scheme") and not pref.enable_scheme_alerts:
            logger.info("NotificationService: scheme alerts disabled for farmer_id={}", farmer_id)
            return await self._create_suppressed_record(
                session, farmer_id, title, message, priority, "Category 'scheme' disabled by user"
            )

        # 3. Check quiet hours (unless URGENT)
        if pref.quiet_hours_enabled and priority != AlertPriority.URGENT:
            if self._is_in_quiet_hours(pref.quiet_hours_start, pref.quiet_hours_end):
                logger.info("NotificationService: suppressed alert for farmer_id={} during quiet hours", farmer_id)
                return await self._create_suppressed_record(
                    session, farmer_id, title, message, priority, "Suppressed during quiet hours"
                )

        # 4. Check notification deduplication (24h cooldown per topic/issue)
        is_dup = await self._deduplicator.is_duplicate_notification(
            farmer_id=farmer_id, alert_type=alert_type, topic_key=topic_key, cooldown_seconds=86400
        )
        if is_dup:
            logger.info("NotificationService: duplicate notification suppressed for farmer_id={} topic='{}'", farmer_id, topic_key)
            return await self._create_suppressed_record(
                session, farmer_id, title, message, priority, "Suppressed by 24h deduplication cooldown"
            )

        # 5. Determine status: if requires_review -> PENDING_REVIEW
        initial_status = AlertStatus.PENDING_REVIEW if requires_review else AlertStatus.CREATED
        channel = pref.preferred_channel

        alert_record = AlertNotificationRecord(
            uuid=uuid4(),
            decision_id=decision_id,
            farmer_id=farmer_id,
            channel=channel,
            title=title,
            message=message,
            priority=priority,
            status=initial_status,
        )
        session.add(alert_record)
        await session.flush()

        # If not held for review, dispatch immediately
        if not requires_review:
            provider = self._providers.get(channel, self._providers[NotificationChannel.IN_APP])
            payload = NotificationPayload(
                farmer_id=farmer_id,
                title=title,
                message=message,
                channel=channel,
                priority=priority,
                language=pref.preferred_language,
                topic_key=topic_key,
                decision_id=decision_id,
                notification_uuid=alert_record.uuid,
            )
            result = await provider.send(payload)
            if result.success:
                alert_record.status = AlertStatus.SENT
                alert_record.sent_at = datetime.now(UTC)
            else:
                alert_record.status = AlertStatus.CANCELLED
                alert_record.review_note = f"Delivery failed: {result.error}"
            await session.flush()

        return alert_record

    async def _get_or_create_preferences(
        self, session: AsyncSession, farmer_id: int
    ) -> NotificationPreferenceRecord:
        """Retrieve existing farmer preference or initialize default."""
        stmt = select(NotificationPreferenceRecord).where(
            NotificationPreferenceRecord.farmer_id == farmer_id
        )
        res = await session.execute(stmt)
        pref = res.scalar_one_or_none()
        if pref is None:
            pref = NotificationPreferenceRecord(
                farmer_id=farmer_id,
                preferred_channel=NotificationChannel.IN_APP,
                preferred_language="te",
                min_severity=RiskSeverity.LOW,
                quiet_hours_enabled=False,
            )
            session.add(pref)
            await session.flush()
        return pref

    async def _create_suppressed_record(
        self,
        session: AsyncSession,
        farmer_id: int,
        title: str,
        message: str,
        priority: AlertPriority,
        reason: str,
    ) -> AlertNotificationRecord:
        """Record a suppressed alert for observability."""
        record = AlertNotificationRecord(
            uuid=uuid4(),
            farmer_id=farmer_id,
            channel=NotificationChannel.IN_APP,
            title=title,
            message=message,
            priority=priority,
            status=AlertStatus.CANCELLED,
            review_note=reason,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    def _is_in_quiet_hours(start_str: str, end_str: str) -> bool:
        """Check if current time is within quiet hours."""
        try:
            now_time = datetime.now(UTC).time()
            s_h, s_m = map(int, start_str.split(":"))
            e_h, e_m = map(int, end_str.split(":"))
            start = time(s_h, s_m)
            end = time(e_h, e_m)
            if start <= end:
                return start <= now_time <= end
            else: # Crosses midnight e.g. 22:00 to 06:00
                return now_time >= start or now_time <= end
        except Exception:
            return False
