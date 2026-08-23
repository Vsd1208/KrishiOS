"""Human-in-the-Loop Agricultural Officer Review Service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.proactive import AlertNotificationRecord, AlertStatus
from app.notifications.contracts import NotificationPayload
from app.notifications.service import NotificationService


class OfficerReviewService:
    """Service enabling Agricultural Officers to inspect, edit, approve, or reject high-impact alerts."""

    async def get_pending_reviews(
        self, session: AsyncSession, offset: int = 0, limit: int = 50
    ) -> list[AlertNotificationRecord]:
        """Fetch all alerts awaiting human review."""
        stmt = (
            select(AlertNotificationRecord)
            .options(
                selectinload(AlertNotificationRecord.farmer),
                selectinload(AlertNotificationRecord.decision),
            )
            .where(AlertNotificationRecord.status == AlertStatus.PENDING_REVIEW)
            .order_by(AlertNotificationRecord.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def approve_alert(
        self,
        session: AsyncSession,
        alert_id: int,
        officer_uuid: UUID,
        review_note: str | None = None,
        edited_message: str | None = None,
        notification_service: NotificationService | None = None,
    ) -> AlertNotificationRecord:
        """Approve a pending alert and dispatch it to the farmer."""
        stmt = (
            select(AlertNotificationRecord)
            .options(selectinload(AlertNotificationRecord.farmer))
            .where(AlertNotificationRecord.id == alert_id)
        )
        res = await session.execute(stmt)
        alert = res.scalar_one_or_none()

        if alert is None:
            raise ValueError(f"Alert with id {alert_id} not found")

        if alert.status != AlertStatus.PENDING_REVIEW:
            raise ValueError(f"Alert id {alert_id} is in status '{alert.status}', cannot approve")

        if edited_message:
            alert.message = edited_message

        alert.status = AlertStatus.APPROVED
        alert.reviewed_by = officer_uuid
        alert.review_note = review_note or "Approved by agricultural officer"
        await session.flush()

        # Dispatch if notification service is provided
        if notification_service is not None:
            provider = notification_service._providers.get(
                alert.channel, notification_service._providers[alert.channel]
            )
            payload = NotificationPayload(
                farmer_id=alert.farmer_id,
                title=alert.title,
                message=alert.message,
                channel=alert.channel,
                priority=alert.priority,
                topic_key="officer_approved",
                decision_id=alert.decision_id,
                notification_uuid=alert.uuid,
            )
            result = await provider.send(payload)
            if result.success:
                alert.status = AlertStatus.SENT
                alert.sent_at = datetime.now(UTC)
            else:
                alert.status = AlertStatus.CANCELLED
                alert.review_note = f"Approved but delivery failed: {result.error}"

        await session.flush()
        logger.info("OfficerReviewService: alert id={} approved by officer_uuid={}", alert_id, officer_uuid)
        return alert

    async def reject_alert(
        self,
        session: AsyncSession,
        alert_id: int,
        officer_uuid: UUID,
        review_note: str,
    ) -> AlertNotificationRecord:
        """Reject and cancel an uncertain or high-impact alert."""
        stmt = select(AlertNotificationRecord).where(AlertNotificationRecord.id == alert_id)
        res = await session.execute(stmt)
        alert = res.scalar_one_or_none()

        if alert is None:
            raise ValueError(f"Alert with id {alert_id} not found")

        alert.status = AlertStatus.CANCELLED
        alert.reviewed_by = officer_uuid
        alert.review_note = f"Rejected: {review_note}"
        await session.flush()

        logger.info("OfficerReviewService: alert id={} rejected by officer_uuid={}", alert_id, officer_uuid)
        return alert
