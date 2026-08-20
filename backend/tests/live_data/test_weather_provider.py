"""Tests for Weather Providers."""

import pytest
from app.live_data.providers.weather_provider import MockWeatherProvider
from app.live_data.schemas.common import FreshnessStatus


@pytest.mark.asyncio
async def test_mock_weather_provider_current_observation():
    provider = MockWeatherProvider()
    obs = await provider.get_current_weather(17.9689, 79.5941)

    assert obs.latitude == 17.9689
    assert obs.longitude == 79.5941
    assert obs.temperature_celsius == 28.5
    assert obs.relative_humidity_percent == 72.0
    assert obs.freshness == FreshnessStatus.FRESH
    assert obs.source is not None


@pytest.mark.asyncio
async def test_mock_weather_provider_forecast():
    provider = MockWeatherProvider()
    fc = await provider.get_forecast(17.9689, 79.5941, days=5)

    assert len(fc.forecast_days) == 5
    assert fc.spray_window_favorable is True
    assert "Moderate rainfall" in fc.summary
