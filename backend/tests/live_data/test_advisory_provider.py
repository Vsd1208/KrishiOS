"""Tests for Advisory Providers."""

import pytest
from app.live_data.providers.advisory_provider import MockAdvisoryProvider
from app.live_data.schemas.advisory import AdvisoryStatus


@pytest.mark.asyncio
async def test_mock_advisory_provider():
    provider = MockAdvisoryProvider()
    advisories = await provider.get_advisories(crop="Paddy", state="Telangana", district="Warangal")

    assert len(advisories) > 0
    adv = advisories[0]
    assert adv.crop == "Paddy"
    assert adv.status == AdvisoryStatus.ACTIVE
    assert "CRIDA" in adv.issuing_authority
    assert len(adv.recommended_practices) > 0
