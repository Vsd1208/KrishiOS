"""Tests for Deterministic Event and Notification Deduplication."""

import pytest

from app.events.contracts import EventEnvelope, EventType
from app.proactive.deduplication import EventDeduplicator


@pytest.mark.asyncio
async def test_event_deduplication_cooldown() -> None:
    """Test that identical events arriving within cooldown window are suppressed (Scenario 4)."""
    dedup = EventDeduplicator(default_cooldown_seconds=3600)

    event1 = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"district": "Nizamabad", "state": "Telangana", "rainfall_mm": 60.0, "date": "2026-08-23"},
    )
    event2_identical = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"district": "Nizamabad", "state": "Telangana", "rainfall_mm": 60.0, "date": "2026-08-23"},
    )
    event3_different_district = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"district": "Warangal", "state": "Telangana", "rainfall_mm": 60.0, "date": "2026-08-23"},
    )

    # First event should not be duplicate
    assert await dedup.is_duplicate_event(event1) is False

    # Second identical event should be recognized as duplicate
    assert await dedup.is_duplicate_event(event2_identical) is True

    # Different district should not be duplicate
    assert await dedup.is_duplicate_event(event3_different_district) is False


@pytest.mark.asyncio
async def test_notification_deduplication() -> None:
    """Test farmer-level notification deduplication for the same issue."""
    dedup = EventDeduplicator()

    # First notification for farmer 101 regarding weather.heavy_rain
    is_dup1 = await dedup.is_duplicate_notification(
        farmer_id=101, alert_type="weather.heavy_rain", topic_key="heavy_rain:paddy"
    )
    assert is_dup1 is False

    # Immediate second alert for same farmer and topic should be suppressed
    is_dup2 = await dedup.is_duplicate_notification(
        farmer_id=101, alert_type="weather.heavy_rain", topic_key="heavy_rain:paddy"
    )
    assert is_dup2 is True

    # Different topic for same farmer should pass
    is_dup3 = await dedup.is_duplicate_notification(
        farmer_id=101, alert_type="market.price_drop", topic_key="price_drop:tomato"
    )
    assert is_dup3 is False

    # Same topic for a different farmer (102) should pass
    is_dup4 = await dedup.is_duplicate_notification(
        farmer_id=102, alert_type="weather.heavy_rain", topic_key="heavy_rain:paddy"
    )
    assert is_dup4 is False
