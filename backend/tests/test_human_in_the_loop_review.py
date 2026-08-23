"""Golden Scenario 5: Human-in-the-Loop Agricultural Officer Review Flow."""

from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.proactive import (
    AlertNotificationRecord,
    AlertPriority,
    AlertStatus,
    NotificationChannel,
    RiskSeverity,
)
from app.notifications.providers import InMemoryNotificationProvider
from app.notifications.service import NotificationService
from app.proactive.review import OfficerReviewService
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.base import RuleResult
from app.events.contracts import EventEnvelope, EventType
from app.proactive.context import FarmerFieldContext


def test_human_in_the_loop_flagging_on_low_confidence() -> None:
    """Ensure high-severity decisions with confidence < 0.80 are flagged for human review."""
    evaluator = RiskEvaluator()

    event = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"rainfall_mm": 110.0, "probability": 0.50}, # Extreme rain, but low probability model
    )
    context = FarmerFieldContext(
        farmer_id=5,
        farmer_name="Balaram",
        phone="9876543215",
        preferred_language="te",
        district_id=1,
        district_name="Nalgonda",
        state_name="Telangana",
        village="Miryalaguda",
        landholding_acres=6.0,
        crop_name="Paddy",
    )
    rule_results = [
        RuleResult(
            matched=True,
            rule_id="RULE_AGRI_HEAVY_RAIN_001",
            risk_type="weather.heavy_rainfall",
            severity=RiskSeverity.CRITICAL,
            confidence=0.72, # Low confidence (< 0.80)
            reason="Uncertain storm system with potential extreme precipitation.",
            recommended_action_summary="Prepare drainage if storm track solidifies.",
        )
    ]

    assessment = evaluator.evaluate(event, context, rule_results)
    assert assessment is not None
    assert assessment.severity == RiskSeverity.CRITICAL
    assert assessment.requires_human_review is True


@pytest.mark.asyncio
async def test_officer_approval_and_rejection_lifecycle() -> None:
    """Test Officer review service approving, modifying, and dispatching an alert."""
    review_service = OfficerReviewService()
    in_memory_provider = InMemoryNotificationProvider()
    notif_service = NotificationService(
        providers={NotificationChannel.IN_APP: in_memory_provider}
    )

    officer_uuid = uuid4()
    mock_session = AsyncMock()

    alert = AlertNotificationRecord(
        id=10,
        uuid=uuid4(),
        farmer_id=5,
        channel=NotificationChannel.IN_APP,
        title="Uncertain Flash Flood Alert",
        message="Preliminary flash flood warning.",
        priority=AlertPriority.URGENT,
        status=AlertStatus.PENDING_REVIEW,
    )

    # Mock database returning this alert
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=alert))
    )
    mock_session.flush = AsyncMock()

    # Officer approves with edited message
    edited_msg = "Official Advisory: Heavy rain expected tomorrow morning. Inspect field bunds."
    approved_alert = await review_service.approve_alert(
        session=mock_session,
        alert_id=10,
        officer_uuid=officer_uuid,
        review_note="Verified with district radar.",
        edited_message=edited_msg,
        notification_service=notif_service,
    )

    assert approved_alert.status == AlertStatus.SENT
    assert approved_alert.reviewed_by == officer_uuid
    assert approved_alert.message == edited_msg
    assert len(in_memory_provider.sent_notifications) == 1
    assert in_memory_provider.sent_notifications[0].message == edited_msg
