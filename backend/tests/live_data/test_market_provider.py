"""Tests for Market Providers."""

import pytest
from app.live_data.providers.market_provider import MockMarketDataProvider


@pytest.mark.asyncio
async def test_mock_market_provider_commodity_prices():
    provider = MockMarketDataProvider()
    prices = await provider.get_commodity_prices("Paddy", state="Telangana", district="Warangal")

    assert len(prices) > 0
    p = prices[0]
    assert p.commodity == "Paddy"
    assert p.modal_price_inr_quintal > 2000.0
    assert p.msp_inr_quintal == 2300.0
    assert p.currency == "INR"


@pytest.mark.asyncio
async def test_mock_market_provider_msp_lookup():
    provider = MockMarketDataProvider()
    msp = await provider.get_msp("Cotton")
    assert msp == 7121.0
