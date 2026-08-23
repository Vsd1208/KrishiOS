"""Tests for Event Envelope and Async Event Bus."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.events.bus import AsyncEventBus
from app.events.contracts import EventEnvelope, EventType


def test_event_envelope_creation_and_serialization() -> None:
    """Test envelope creation, immutability, and JSON serialization."""
    event_id = uuid4()
    correlation_id = uuid4()
    now = datetime.now(UTC)

    envelope = EventEnvelope(
        event_id=event_id,
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        source="open_meteo_poller",
        timestamp=now,
        correlation_id=correlation_id,
        payload={"rainfall_mm": 75.0, "district": "Nizamabad"},
        metadata={"priority": "high"},
    )

    data = envelope.to_dict()
    assert data["event_id"] == str(event_id)
    assert data["event_type"] == EventType.HEAVY_RAIN_EXPECTED
    assert data["source"] == "open_meteo_poller"
    assert data["correlation_id"] == str(correlation_id)
    assert data["payload"]["rainfall_mm"] == 75.0

    restored = EventEnvelope.from_dict(data)
    assert restored.event_id == event_id
    assert restored.event_type == EventType.HEAVY_RAIN_EXPECTED
    assert restored.correlation_id == correlation_id
    assert restored.payload["district"] == "Nizamabad"


@pytest.mark.asyncio
async def test_async_event_bus_exact_and_wildcard_routing() -> None:
    """Test event delivery with exact matches and wildcard routing."""
    bus = AsyncEventBus()
    received_exact: list[EventEnvelope] = []
    received_weather_wildcard: list[EventEnvelope] = []
    received_all_wildcard: list[EventEnvelope] = []

    async def exact_handler(event: EventEnvelope) -> None:
        received_exact.append(event)

    async def weather_wildcard_handler(event: EventEnvelope) -> None:
        received_weather_wildcard.append(event)

    async def all_wildcard_handler(event: EventEnvelope) -> None:
        received_all_wildcard.append(event)

    bus.subscribe(EventType.HEAVY_RAIN_EXPECTED, exact_handler)
    bus.subscribe("weather.*", weather_wildcard_handler)
    bus.subscribe("*", all_wildcard_handler)

    weather_event = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={"rainfall_mm": 55.0},
    )
    market_event = EventEnvelope(
        event_type=EventType.MARKET_PRICE_CHANGED,
        payload={"commodity": "Paddy", "change_percent": -12.0},
    )

    await bus.publish(weather_event)
    await bus.publish(market_event)

    assert len(received_exact) == 1
    assert received_exact[0].event_type == EventType.HEAVY_RAIN_EXPECTED

    assert len(received_weather_wildcard) == 1
    assert received_weather_wildcard[0].event_type == EventType.HEAVY_RAIN_EXPECTED

    assert len(received_all_wildcard) == 2


@pytest.mark.asyncio
async def test_async_event_bus_error_isolation() -> None:
    """Ensure a failing handler does not prevent other handlers from executing."""
    bus = AsyncEventBus()
    successful_deliveries: list[EventEnvelope] = []

    async def failing_handler(event: EventEnvelope) -> None:
        raise RuntimeError("Handler crash")

    async def healthy_handler(event: EventEnvelope) -> None:
        successful_deliveries.append(event)

    bus.subscribe(EventType.WEATHER_ALERT, failing_handler)
    bus.subscribe(EventType.WEATHER_ALERT, healthy_handler)

    event = EventEnvelope(event_type=EventType.WEATHER_ALERT, payload={"alert": "heatwave"})
    await bus.publish(event)

    assert len(successful_deliveries) == 1
    assert successful_deliveries[0].payload["alert"] == "heatwave"
