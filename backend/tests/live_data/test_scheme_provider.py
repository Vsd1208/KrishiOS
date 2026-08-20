"""Tests for Government Scheme Provider."""

import pytest
from app.live_data.providers.scheme_provider import MockGovernmentSchemeProvider


@pytest.mark.asyncio
async def test_mock_scheme_provider_filtering():
    provider = MockGovernmentSchemeProvider()
    schemes = await provider.get_schemes(state="Telangana", crop="Paddy", farmer_category="Small")

    assert len(schemes) >= 2  # Central PM-KISAN, PMFBY, and TS Rythu Bharosa
    scheme_ids = [s.scheme_id for s in schemes]
    assert "GOI-PM-KISAN" in scheme_ids
    assert "TS-RYTHU-BHAROSA" in scheme_ids


@pytest.mark.asyncio
async def test_mock_scheme_provider_get_by_id():
    provider = MockGovernmentSchemeProvider()
    scheme = await provider.get_scheme_by_id("GOI-PM-KISAN")

    assert scheme is not None
    assert scheme.name == "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)"
    assert scheme.status == "Active"
