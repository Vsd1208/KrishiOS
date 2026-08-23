"""Tests for Farmer Notification Preferences and Quiet Hours."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.models.proactive import (
    AlertPriority,
    AlertStatus,
    NotificationChannel,
    NotificationPreferenceRecord,
    RiskSeverity,
)
from app.notifications.providers import InMemoryNotificationProvider
from app.notifications.service import NotificationService
from app.proactive.deduplication import EventDeduplicator


@pytest.mark.asyncio
async def test_category_preference_toggles() -> None:
    """Ensure notifications for disabled categories are suppressed."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    in_memory_provider = InMemoryNotificationProvider()
    notif_service = NotificationService(
        providers={NotificationChannel.IN_APP: in_memory_provider}
    )

    # Farmer with weather alerts disabled
    pref_no_weather = NotificationPreferenceRecord(
        farmer_id=20,
        preferred_channel=NotificationChannel.IN_APP,
        enable_weather_alerts=False,
        enable_disease_alerts=True,
    )
    notif_service._get_or_create_preferences = AsyncMock(return_value=pref_no_weather)

    record = await notif_service.dispatch_alert(
        session=mock_session,
        farmer_id=20,
        title="Heavy Rain",
        message="Rain forecast",
        alert_type="weather.heavy_rain",
        topic_key="heavy_rain:paddy",
    )

    assert record.status == AlertStatus.CANCELLED
    assert "disabled by user" in record.review_note
    assert len(in_memory_provider.sent_notifications) == 0


@pytest.mark.asyncio
async def test_quiet_hours_suppression_and_urgent_override() -> None:
    """Test quiet hours suppression for NORMAL priority, and pass-through for URGENT."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    in_memory_provider = InMemoryNotificationProvider()
    notif_service = NotificationService(
        providers={NotificationChannel.IN_APP: in_memory_provider}
    )
    notif_service._is_in_quiet_hours = MagicMock(return_value=True)

    pref_quiet = NotificationPreferenceRecord(
        farmer_id=21,
        preferred_channel=NotificationChannel.IN_APP,
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="06:00",
        enable_weather_alerts=True,
        enable_disease_alerts=True,
        enable_market_alerts=True,
        enable_scheme_alerts=True,
    )
    notif_service._get_or_create_preferences = AsyncMock(return_value=pref_quiet)

    # 1. Normal priority alert during quiet hours -> Suppressed
    rec_normal = await notif_service.dispatch_alert(
        session=mock_session,
        farmer_id=21,
        title="Advisory Update",
        message="General advisory update",
        alert_type="agronomy.advisory",
        topic_key="advisory:paddy",
        priority=AlertPriority.NORMAL,
    )
    assert rec_normal.status == AlertStatus.CANCELLED
    assert "quiet hours" in rec_normal.review_note
    assert len(in_memory_provider.sent_notifications) == 0

    # 2. URGENT alert during quiet hours -> Overrides quiet hours and is delivered
    rec_urgent = await notif_service.dispatch_alert(
        session=mock_session,
        farmer_id=21,
        title="Cyclone Warning",
        message="Immediate action required",
        alert_type="weather.cyclone",
        topic_key="cyclone:warning",
        priority=AlertPriority.URGENT,
    )
    assert rec_urgent.status == AlertStatus.SENT
    assert len(in_memory_provider.sent_notifications) == 1
