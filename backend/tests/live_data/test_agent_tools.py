"""Tests for Live Agent Tools."""

import pytest
from app.agents.tools.govt_scheme import GovernmentSchemeTool
from app.agents.tools.live_advisory import LiveAdvisoryTool
from app.agents.tools.live_weather import LiveWeatherTool
from app.agents.tools.mandi_price import MandiPriceTool


@pytest.mark.asyncio
async def test_live_weather_tool_execution():
    tool = LiveWeatherTool()
    res = await tool.execute({"district": "Warangal", "state": "Telangana", "forecast_days": 3})

    assert res.success is True
    assert "current" in res.data
    assert "forecast" in res.data
    assert res.data["current"]["temperature_celsius"] > 0


@pytest.mark.asyncio
async def test_mandi_price_tool_execution():
    tool = MandiPriceTool()
    res = await tool.execute({"commodity": "Paddy", "state": "Telangana", "district": "Warangal"})

    assert res.success is True
    assert res.data["commodity"] == "Paddy"
    assert res.data["modal_price_inr_quintal"] > 0


@pytest.mark.asyncio
async def test_live_advisory_tool_execution():
    tool = LiveAdvisoryTool()
    res = await tool.execute({"crop": "Paddy", "state": "Telangana", "district": "Warangal"})

    assert res.success is True
    assert res.data["crop"] == "Paddy"
    assert "content" in res.data


@pytest.mark.asyncio
async def test_government_scheme_tool_execution():
    tool = GovernmentSchemeTool()
    res = await tool.execute({"state": "Telangana", "crop": "Paddy"})

    assert res.success is True
    assert res.data["schemes_count"] > 0
