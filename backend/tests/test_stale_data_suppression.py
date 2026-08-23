"""Golden Scenario 6: Stale External Data Penalty and Suppression."""

from datetime import UTC, datetime, timedelta
import pytest

from app.events.contracts import EventEnvelope, EventType
from app.models.proactive import RiskSeverity
from app.proactive.context import FarmerFieldContext
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.base import RuleResult


def test_stale_data_confidence_penalty_and_freshness_tracking() -> None:
    """Golden Scenario 6: Data older than 72 hours incurs confidence penalty and explicit freshness annotation."""
    evaluator = RiskEvaluator()

    # Event generated 4 days ago (96 hours stale)
    stale_time = datetime.now(UTC) - timedelta(days=4)
    stale_event = EventEnvelope(
        event_type=EventType.WEATHER_ALERT,
        payload={"rainfall_mm": 80.0, "probability": 0.90},
        timestamp=stale_time,
    )

    context = FarmerFieldContext(
        farmer_id=8,
        farmer_name="Govind",
        phone="9876543218",
        preferred_language="te",
        district_id=3,
        district_name="Medak",
        state_name="Telangana",
        village="Siddipet",
        landholding_acres=4.0,
        crop_name="Paddy",
    )

    rule_results = [
        RuleResult(
            matched=True,
            rule_id="RULE_AGRI_HEAVY_RAIN_001",
            risk_type="weather.heavy_rainfall",
            severity=RiskSeverity.HIGH,
            confidence=0.90, # Rule initial confidence was high
            reason="Heavy rainfall detected.",
        )
    ]

    assessment = evaluator.evaluate(stale_event, context, rule_results)
    assert assessment is not None

    # Stale event penalty should have cut confidence in half (0.90 * 0.5 = 0.45)
    assert assessment.confidence <= 0.50
    assert assessment.evidence_package.data_freshness_seconds >= 300000
    assert assessment.evidence_package.confidence_breakdown["event_age_penalty"] == 0.5
    # Since confidence is now < 0.80 and severity is HIGH, it automatically requires human review
    assert assessment.requires_human_review is True
