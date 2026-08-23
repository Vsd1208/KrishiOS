"""Tests for the Agricultural Relevance and Rule Engine."""

import pytest

from app.events.contracts import EventEnvelope, EventType
from app.models.proactive import RiskSeverity
from app.proactive.rules.agricultural_rules import (
    DiseaseRiskRule,
    ExtremeHeatRule,
    HeavyRainfallRule,
    MarketPriceVolatilityRule,
    RuleRegistry,
    SchemeEligibilityRule,
)


@pytest.mark.asyncio
async def test_heavy_rainfall_rule() -> None:
    """Test Heavy Rainfall rule with various precipitation levels and soil types."""
    rule = HeavyRainfallRule()

    # Case 1: Low rainfall (20mm) -> should not match
    event_low = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"rainfall_mm": 20.0},
    )
    res_low = await rule.evaluate(event_low, {"crop": "Paddy", "soil_type": "Clay"})
    assert res_low.matched is False

    # Case 2: High rainfall (75mm) with clay soil -> should match with HIGH severity
    event_high = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"rainfall_mm": 75.0, "probability": 0.9},
    )
    res_high = await rule.evaluate(event_high, {"crop": "Paddy", "soil_type": "Black Clay"})
    assert res_high.matched is True
    assert res_high.severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]
    assert res_high.confidence >= 0.85
    assert "drainage" in res_high.recommended_action_summary.lower()


@pytest.mark.asyncio
async def test_disease_risk_rule() -> None:
    """Test fungal disease risk evaluation based on microclimate."""
    rule = DiseaseRiskRule()

    # Case 1: Low humidity (45%) -> no disease risk match
    event_dry = EventEnvelope(
        event_type=EventType.HIGH_HUMIDITY,
        payload={"relative_humidity_percent": 45.0, "temperature_celsius": 28.0},
    )
    res_dry = await rule.evaluate(event_dry, {"crop": "Paddy"})
    assert res_dry.matched is False

    # Case 2: High humidity (88%) + favorable temperature (26°C) for susceptible crop
    event_humid = EventEnvelope(
        event_type=EventType.HIGH_HUMIDITY,
        payload={"relative_humidity_percent": 88.0, "temperature_celsius": 26.0},
    )
    res_humid = await rule.evaluate(event_humid, {"crop": "Paddy"})
    assert res_humid.matched is True
    assert res_humid.risk_type == "agronomy.disease_risk"
    assert "microclimate" in res_humid.reason.lower()


@pytest.mark.asyncio
async def test_market_price_volatility_rule() -> None:
    """Test mandi price movement detection."""
    rule = MarketPriceVolatilityRule()

    # Case 1: Minor 3% price shift -> should not trigger alert
    event_minor = EventEnvelope(
        event_type=EventType.MARKET_PRICE_CHANGED,
        payload={"commodity": "Tomato", "change_percent": -3.0, "current_price": 2100.0},
    )
    res_minor = await rule.evaluate(event_minor, {"crop": "Tomato"})
    assert res_minor.matched is False

    # Case 2: Major -18% price drop for farmer's crop
    event_major = EventEnvelope(
        event_type=EventType.MARKET_PRICE_CHANGED,
        payload={"commodity": "Tomato", "change_percent": -18.0, "current_price": 1400.0},
    )
    res_major = await rule.evaluate(event_major, {"crop": "Tomato"})
    assert res_major.matched is True
    assert res_major.severity == RiskSeverity.MEDIUM
    assert "18.0%" in res_major.reason
    assert "dropped" in res_major.reason


@pytest.mark.asyncio
async def test_scheme_eligibility_rule() -> None:
    """Test government scheme eligibility checking."""
    rule = SchemeEligibilityRule()

    event = EventEnvelope(
        event_type=EventType.GOVERNMENT_SCHEME_UPDATED,
        payload={
            "scheme_name": "Rythu Bandhu Input Support",
            "state": "Telangana",
            "max_landholding_acres": 10.0,
            "application_deadline": "2026-09-15",
        },
    )

    # Farmer in Telangana with 4.5 acres -> Eligible
    res_eligible = await rule.evaluate(event, {"state": "Telangana", "landholding_acres": 4.5})
    assert res_eligible.matched is True
    assert res_eligible.severity == RiskSeverity.LOW

    # Farmer in Punjab -> Ineligible (state mismatch)
    res_ineligible = await rule.evaluate(event, {"state": "Punjab", "landholding_acres": 4.5})
    assert res_ineligible.matched is False
