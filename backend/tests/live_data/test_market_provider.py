"""Tests for Market Providers."""

import pytest
from app.live_data.providers.market_provider import (
    AgmarknetMarketProvider,
    MockMarketDataProvider,
    official_msp,
)
from app.providers import ProviderConfigurationError


@pytest.mark.asyncio
async def test_mock_market_provider_commodity_prices():
    provider = MockMarketDataProvider()
    prices = await provider.get_commodity_prices("Paddy", state="Telangana", district="Warangal")

    assert len(prices) > 0
    p = prices[0]
    assert p.commodity == "Paddy"
    assert p.modal_price_inr_quintal > 2000.0
    assert p.msp_inr_quintal == 2441.0  # PIB, KMS 2026-27
    assert p.currency == "INR"


@pytest.mark.asyncio
async def test_mock_market_provider_msp_lookup():
    provider = MockMarketDataProvider()
    msp = await provider.get_msp("Cotton")
    assert msp == 8267.0  # cotton medium staple, PIB KMS 2026-27


@pytest.mark.asyncio
async def test_msp_only_from_the_official_reference():
    provider = MockMarketDataProvider()
    assert await provider.get_msp("Tomato") is None  # no MSP exists for tomato
    assert await provider.get_msp("Wheat") is None  # Rabi MSP not in the reference yet
    p = (await provider.get_commodity_prices("Paddy"))[0]
    assert "not official" in p.source and p.authority_level.value == "UNVERIFIED_EXTERNAL_SOURCE"


def test_agmarknet_needs_a_key():
    with pytest.raises(ProviderConfigurationError):
        AgmarknetMarketProvider(api_base_url="https://x", api_key=None, resource_id="r")


@pytest.mark.asyncio
async def test_agmarknet_parses_official_records(monkeypatch):
    provider = AgmarknetMarketProvider(api_base_url="https://x", api_key="k", resource_id="r")
    records = [
        {"state": "Telangana", "district": "Khammam", "market": "Khammam",
         "commodity": "Paddy(Dhan)(Common)", "variety": "1001", "arrival_date": "13/11/2026",
         "min_price": "2200", "max_price": "2460", "modal_price": "2400"},
        {"state": "Telangana", "district": "Khammam", "market": "Khammam",
         "commodity": "Cotton", "variety": "Other", "arrival_date": "13/11/2026",
         "min_price": "7000", "max_price": "8100", "modal_price": "7800"},
        {"state": "Telangana", "district": "Khammam", "market": "Madhira",
         "commodity": "Paddy(Dhan)(Common)", "variety": "1001", "arrival_date": "12/11/2026",
         "min_price": "", "max_price": "", "modal_price": ""},  # incomplete: dropped
    ]

    async def fake_fetch(state, district, limit=500):
        return records

    monkeypatch.setattr(provider, "fetch_records", fake_fetch)
    prices = await provider.get_commodity_prices("paddy", "Telangana", "Khammam")
    assert len(prices) == 1
    p = prices[0]
    assert p.modal_price_inr_quintal == 2400 and p.msp_inr_quintal == 2441
    assert p.authority_level.value == "GOVERNMENT" and "data.gov.in" in p.source


def test_msp_follows_the_grade_in_the_official_commodity_name():
    assert official_msp("Paddy(Fine/Superfine/Grade A)")["msp_inr_quintal"] == 2461
    assert official_msp("Paddy(Common)")["msp_inr_quintal"] == 2441
    assert official_msp("Cotton", "Long Staple")["msp_inr_quintal"] == 8667
    assert official_msp("Cotton", "Cotton (Unginned)")["msp_inr_quintal"] == 8267
    assert official_msp("Tomato") is None
