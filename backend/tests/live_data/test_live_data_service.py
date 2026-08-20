"""Tests for LiveDataService."""

import pytest
from app.live_data.schemas.common import FreshnessStatus
from app.live_data.schemas.scheme import SchemeEligibility
from app.live_data.services.live_data_service import LiveDataService


@pytest.mark.asyncio
async def test_live_data_service_weather_and_caching():
    service = LiveDataService()

    # 1. First call fetches fresh data
    obs1 = await service.get_current_weather(latitude=17.9689, longitude=79.5941)
    assert obs1.freshness == FreshnessStatus.FRESH
    assert obs1.cached is False

    # 2. Second call serves from cache
    obs2 = await service.get_current_weather(latitude=17.9689, longitude=79.5941)
    assert obs2.cached is True
    assert obs2.temperature_celsius == obs1.temperature_celsius


@pytest.mark.asyncio
async def test_live_data_service_scheme_eligibility_evaluation():
    service = LiveDataService()

    # Eligible case: Small farmer in Telangana with Paddy
    eval_res = await service.evaluate_scheme_eligibility(
        scheme_id="TS-RYTHU-BHAROSA",
        landholding_acres=3.5,
        crop="Paddy",
        state="Telangana",
        farmer_category="Small",
    )
    assert eval_res.eligibility == SchemeEligibility.ELIGIBLE

    # Missing information case -> UNKNOWN (no fabrication)
    eval_unknown = await service.evaluate_scheme_eligibility(
        scheme_id="TS-RYTHU-BHAROSA",
        landholding_acres=None,
        state=None,
    )
    assert eval_unknown.eligibility == SchemeEligibility.UNKNOWN
    assert "landholding_acres" in eval_unknown.missing_criteria
