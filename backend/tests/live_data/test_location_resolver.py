"""Tests for LocationResolver."""

import pytest
from app.live_data.services.location_resolver import LocationResolver


@pytest.mark.asyncio
async def test_location_resolver_explicit_coordinates():
    resolver = LocationResolver()
    loc = await resolver.resolve(latitude=17.5, longitude=78.5, state="Telangana", district="Hyderabad")

    assert loc.latitude == 17.5
    assert loc.longitude == 78.5
    assert loc.state == "Telangana"
    assert loc.district == "Hyderabad"
    assert loc.privacy_coords == (17.5, 78.5)


@pytest.mark.asyncio
async def test_location_resolver_default_fallback():
    resolver = LocationResolver()
    loc = await resolver.resolve()

    assert loc.latitude == LocationResolver.DEFAULT_LAT
    assert loc.longitude == LocationResolver.DEFAULT_LON
    assert loc.district == LocationResolver.DEFAULT_DISTRICT
    assert loc.is_approximate is True
