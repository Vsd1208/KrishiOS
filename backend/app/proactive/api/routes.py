"""REST API routes for Proactive Agricultural Decision Intelligence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission, get_current_auth_context
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.events.contracts import EventEnvelope
from app.models.proactive import (
    AlertNotificationRecord,
    AlertStatus,
    NotificationPreferenceRecord,
    ProactiveDecisionRecord,
)
from app.models.user import UserRole
from app.notifications.service import NotificationService
from app.proactive.api.dependencies import (
    get_event_processor,
    get_notification_service,
    get_officer_review_service,
)
from app.proactive.api.schemas import (
    AlertNotificationResponse,
    EventIngestRequest,
    EventIngestResponse,
    NotificationPreferenceRequest,
    NotificationPreferenceResponse,
    OfficerReviewActionRequest,
    ProactiveDecisionResponse,
)
from app.proactive.processor import EventProcessor
from app.proactive.review import OfficerReviewService

router = APIRouter(prefix="/proactive", tags=["Proactive Decision Intelligence"])


# ── Ingest External/Internal Event ────────────────────────────────────────────
@router.post(
    "/events",
    response_model=EventIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RequirePermission(Permission.PROACTIVE_EVENT_EMIT))],
)
async def ingest_event(
    request: EventIngestRequest,
    processor: EventProcessor = Depends(get_event_processor),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> EventIngestResponse:
    """Ingest an external or internal agricultural event into the proactive processing pipeline."""
    envelope = EventEnvelope(
        event_type=request.event_type,
        payload=request.payload,
        source=request.source,
        correlation_id=request.correlation_id,
    )

    decisions = await processor.process_event(session, envelope)
    await session.commit()

    return EventIngestResponse(
        event_id=envelope.event_id,
        status="processed",
        decisions_count=len(decisions),
        message=f"Event processed successfully. Generated {len(decisions)} proactive decisions.",
    )


# ── Query Proactive Decisions & Evidence ──────────────────────────────────────
@router.get(
    "/decisions",
    response_model=list[ProactiveDecisionResponse],
    dependencies=[Depends(RequirePermission(Permission.PROACTIVE_DECISION_READ))],
)
async def list_decisions(
    farmer_id: int | None = Query(None, description="Filter by farmer ID"),
    risk_type: str | None = Query(None, description="Filter by risk type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[ProactiveDecisionResponse]:
    """Query past proactive decisions, risk evaluations, and evidence packages."""
    stmt = select(ProactiveDecisionRecord).order_by(ProactiveDecisionRecord.created_at.desc())

    # Farmer scope ownership check
    if auth.role == UserRole.FARMER:
        if not auth.farmer_profile_id:
            return []
        stmt = stmt.where(ProactiveDecisionRecord.farmer_id == auth.farmer_profile_id)
    elif farmer_id:
        stmt = stmt.where(ProactiveDecisionRecord.farmer_id == farmer_id)

    if risk_type:
        stmt = stmt.where(ProactiveDecisionRecord.risk_type.ilike(f"%{risk_type}%"))

    stmt = stmt.offset(offset).limit(limit)
    res = await session.execute(stmt)
    decisions = res.scalars().all()

    return [
        ProactiveDecisionResponse(
            decision_id=d.decision_id,
            event_id=d.event_id,
            farmer_id=d.farmer_id,
            field_id=d.field_id,
            risk_type=d.risk_type,
            risk_severity=d.risk_severity,
            confidence=d.confidence,
            evidence_package=d.evidence_package,
            advisory_text=d.advisory_text,
            requires_review=d.requires_review,
            valid_until=d.valid_until,
            created_at=d.created_at,
        )
        for d in decisions
    ]


# ── Farmer Alerts & Notifications ─────────────────────────────────────────────
@router.get(
    "/alerts",
    response_model=list[AlertNotificationResponse],
    dependencies=[Depends(RequirePermission(Permission.ALERT_READ))],
)
async def list_alerts(
    farmer_id: int | None = Query(None, description="Filter by farmer ID"),
    status_filter: AlertStatus | None = Query(None, description="Filter by alert status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> list[AlertNotificationResponse]:
    """List alerts for the current farmer or for a specified farmer (officer view)."""
    stmt = select(AlertNotificationRecord).order_by(AlertNotificationRecord.created_at.desc())

    if auth.role == UserRole.FARMER:
        if not auth.farmer_profile_id:
            return []
        stmt = stmt.where(AlertNotificationRecord.farmer_id == auth.farmer_profile_id)
    elif farmer_id:
        stmt = stmt.where(AlertNotificationRecord.farmer_id == farmer_id)

    if status_filter:
        stmt = stmt.where(AlertNotificationRecord.status == status_filter)

    stmt = stmt.offset(offset).limit(limit)
    res = await session.execute(stmt)
    alerts = res.scalars().all()

    return [
        AlertNotificationResponse(
            id=a.id,
            uuid=a.uuid,
            decision_id=a.decision_id,
            farmer_id=a.farmer_id,
            channel=a.channel,
            title=a.title,
            message=a.message,
            priority=a.priority,
            status=a.status,
            reviewed_by=a.reviewed_by,
            review_note=a.review_note,
            sent_at=a.sent_at,
            acknowledged_at=a.acknowledged_at,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertNotificationResponse,
    dependencies=[Depends(RequirePermission(Permission.ALERT_ACKNOWLEDGE))],
)
async def acknowledge_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> AlertNotificationResponse:
    """Acknowledge receipt and reading of an alert notification."""
    stmt = select(AlertNotificationRecord).where(AlertNotificationRecord.id == alert_id)
    res = await session.execute(stmt)
    alert = res.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert notification not found")

    # Ownership check
    if auth.role == UserRole.FARMER and alert.farmer_id != auth.farmer_profile_id:
        raise HTTPException(status_code=403, detail="Not authorized to acknowledge another farmer's alert")

    from datetime import UTC, datetime
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(UTC)
    await session.commit()

    return AlertNotificationResponse(
        id=alert.id,
        uuid=alert.uuid,
        decision_id=alert.decision_id,
        farmer_id=alert.farmer_id,
        channel=alert.channel,
        title=alert.title,
        message=alert.message,
        priority=alert.priority,
        status=alert.status,
        reviewed_by=alert.reviewed_by,
        review_note=alert.review_note,
        sent_at=alert.sent_at,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at,
    )


# ── Human-in-the-Loop Officer Reviews ─────────────────────────────────────────
@router.get(
    "/reviews",
    response_model=list[AlertNotificationResponse],
    dependencies=[Depends(RequirePermission(Permission.ALERT_REVIEW))],
)
async def list_pending_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    review_service: OfficerReviewService = Depends(get_officer_review_service),
    session: AsyncSession = Depends(get_db_session),
) -> list[AlertNotificationResponse]:
    """List high-impact and uncertain alerts awaiting agricultural officer sign-off."""
    pending = await review_service.get_pending_reviews(session, offset=offset, limit=limit)
    return [
        AlertNotificationResponse(
            id=a.id,
            uuid=a.uuid,
            decision_id=a.decision_id,
            farmer_id=a.farmer_id,
            channel=a.channel,
            title=a.title,
            message=a.message,
            priority=a.priority,
            status=a.status,
            reviewed_by=a.reviewed_by,
            review_note=a.review_note,
            sent_at=a.sent_at,
            acknowledged_at=a.acknowledged_at,
            created_at=a.created_at,
        )
        for a in pending
    ]


@router.post(
    "/reviews/{alert_id}/action",
    response_model=AlertNotificationResponse,
    dependencies=[Depends(RequirePermission(Permission.ALERT_REVIEW))],
)
async def take_review_action(
    alert_id: int,
    request: OfficerReviewActionRequest,
    review_service: OfficerReviewService = Depends(get_officer_review_service),
    notification_service: NotificationService = Depends(get_notification_service),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> AlertNotificationResponse:
    """Approve or reject a pending alert with optional notes or edited message."""
    action = request.action.upper().strip()
    try:
        if action == "APPROVE":
            alert = await review_service.approve_alert(
                session=session,
                alert_id=alert_id,
                officer_uuid=auth.user_uuid,
                review_note=request.review_note,
                edited_message=request.edited_message,
                notification_service=notification_service,
            )
        elif action == "REJECT":
            alert = await review_service.reject_alert(
                session=session,
                alert_id=alert_id,
                officer_uuid=auth.user_uuid,
                review_note=request.review_note or "Rejected by officer",
            )
        else:
            raise HTTPException(status_code=400, detail="Action must be 'APPROVE' or 'REJECT'")

        await session.commit()
        return AlertNotificationResponse(
            id=alert.id,
            uuid=alert.uuid,
            decision_id=alert.decision_id,
            farmer_id=alert.farmer_id,
            channel=alert.channel,
            title=alert.title,
            message=alert.message,
            priority=alert.priority,
            status=alert.status,
            reviewed_by=alert.reviewed_by,
            review_note=alert.review_note,
            sent_at=alert.sent_at,
            acknowledged_at=alert.acknowledged_at,
            created_at=alert.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Farmer Notification Preferences ───────────────────────────────────────────
@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    dependencies=[Depends(RequirePermission(Permission.PREFERENCE_READ))],
)
async def get_preferences(
    farmer_id: int | None = Query(None, description="Farmer ID for officers"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> NotificationPreferenceResponse:
    """Retrieve notification preferences, quiet hours, and channel configuration."""
    target_farmer_id = auth.farmer_profile_id if auth.role == UserRole.FARMER else (farmer_id or auth.farmer_profile_id)
    if not target_farmer_id:
        raise HTTPException(status_code=400, detail="Farmer profile ID required")

    stmt = select(NotificationPreferenceRecord).where(
        NotificationPreferenceRecord.farmer_id == target_farmer_id
    )
    res = await session.execute(stmt)
    pref = res.scalar_one_or_none()

    if pref is None:
        from app.models.proactive import NotificationChannel, RiskSeverity
        pref = NotificationPreferenceRecord(
            farmer_id=target_farmer_id,
            preferred_channel=NotificationChannel.IN_APP,
            preferred_language="te",
            min_severity=RiskSeverity.LOW,
            quiet_hours_enabled=False,
        )
        session.add(pref)
        await session.commit()

    return NotificationPreferenceResponse(
        id=pref.id,
        farmer_id=pref.farmer_id,
        preferred_channel=pref.preferred_channel,
        preferred_language=pref.preferred_language,
        min_severity=pref.min_severity,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        enable_weather_alerts=pref.enable_weather_alerts,
        enable_disease_alerts=pref.enable_disease_alerts,
        enable_market_alerts=pref.enable_market_alerts,
        enable_scheme_alerts=pref.enable_scheme_alerts,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    dependencies=[Depends(RequirePermission(Permission.PREFERENCE_UPDATE))],
)
async def update_preferences(
    request: NotificationPreferenceRequest,
    farmer_id: int | None = Query(None, description="Farmer ID for officers"),
    session: AsyncSession = Depends(get_db_session),
    auth: AuthContext = Depends(get_current_auth_context),
) -> NotificationPreferenceResponse:
    """Update notification preferences, quiet hours, and active categories."""
    target_farmer_id = auth.farmer_profile_id if auth.role == UserRole.FARMER else (farmer_id or auth.farmer_profile_id)
    if not target_farmer_id:
        raise HTTPException(status_code=400, detail="Farmer profile ID required")

    stmt = select(NotificationPreferenceRecord).where(
        NotificationPreferenceRecord.farmer_id == target_farmer_id
    )
    res = await session.execute(stmt)
    pref = res.scalar_one_or_none()

    if pref is None:
        pref = NotificationPreferenceRecord(farmer_id=target_farmer_id)
        session.add(pref)

    pref.preferred_channel = request.preferred_channel
    pref.preferred_language = request.preferred_language
    pref.min_severity = request.min_severity
    pref.quiet_hours_enabled = request.quiet_hours_enabled
    pref.quiet_hours_start = request.quiet_hours_start
    pref.quiet_hours_end = request.quiet_hours_end
    pref.enable_weather_alerts = request.enable_weather_alerts
    pref.enable_disease_alerts = request.enable_disease_alerts
    pref.enable_market_alerts = request.enable_market_alerts
    pref.enable_scheme_alerts = request.enable_scheme_alerts

    await session.commit()
    return NotificationPreferenceResponse(
        id=pref.id,
        farmer_id=pref.farmer_id,
        preferred_channel=pref.preferred_channel,
        preferred_language=pref.preferred_language,
        min_severity=pref.min_severity,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        enable_weather_alerts=pref.enable_weather_alerts,
        enable_disease_alerts=pref.enable_disease_alerts,
        enable_market_alerts=pref.enable_market_alerts,
        enable_scheme_alerts=pref.enable_scheme_alerts,
        created_at=pref.created_at,
        updated_at=pref.updated_at,
    )
