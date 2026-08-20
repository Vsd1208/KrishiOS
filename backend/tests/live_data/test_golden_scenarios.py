"""Golden Scenarios for Sprint 9 Live Agricultural Intelligence."""

from datetime import UTC, datetime, timedelta
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.agents.crop_advisory_agent import CropAdvisoryAgent
from app.agents.execution.context import ExecutionContext
from app.agents.providers.llm import MockLocalLLMProvider
from app.agents.tools.govt_scheme import GovernmentSchemeTool
from app.agents.tools.knowledge_search import KnowledgeSearchTool
from app.agents.tools.live_advisory import LiveAdvisoryTool
from app.agents.tools.live_weather import LiveWeatherTool
from app.agents.tools.mandi_price import MandiPriceTool
from app.api.dependencies.auth import AuthContext
from app.auth.permissions import Permission
from app.live_data.schemas.common import FreshnessStatus
from app.live_data.schemas.scheme import SchemeEligibility
from app.live_data.services.live_data_service import LiveDataService


@pytest.mark.asyncio
async def test_scenario_1_weather_query():
    """SCENARIO 1 — WEATHER: Farmer asks 'What will the weather be like tomorrow?'"""
    weather_tool = LiveWeatherTool()
    res = await weather_tool.execute({"district": "Warangal", "state": "Telangana", "forecast_days": 3})

    assert res.success is True
    assert res.data["current"]["freshness"] == "FRESH"
    assert len(res.data["forecast"]["days"]) == 3
    assert res.data["forecast"]["spray_window_favorable"] is True


@pytest.mark.asyncio
async def test_scenario_2_agricultural_spray_decision():
    """SCENARIO 2 — AGRICULTURAL DECISION: Farmer asks 'Should I spray my paddy crop tomorrow?'"""
    llm = MockLocalLLMProvider()

    class MockItem:
        class Hit:
            chunk_text = "Spray tricyclazole 75% WP @ 0.6g/L for blast. Do not spray if rain is expected within 24 hours."
        class Citation:
            title = "ICAR Guidelines (2026)"
            source = "ICAR"
            source_url = "https://icar.org.in"
            page_number = 42

        hit = Hit()
        citation = Citation()
        ranking_score = 0.92
        freshness_score = 1.0
        authority_score = 1.0
        answer_context = "Spray tricyclazole"

    class MockSearchResult:
        query = "Should I spray my paddy crop tomorrow?"
        latency_ms = 12.0
        results = [MockItem()]

    mock_pipeline = AsyncMock()
    mock_pipeline.search = AsyncMock(return_value=MockSearchResult())
    search_tool = KnowledgeSearchTool(pipeline=mock_pipeline)
    weather_tool = LiveWeatherTool()
    advisory_tool = LiveAdvisoryTool()

    agent = CropAdvisoryAgent(
        llm_provider=llm,
        search_tool=search_tool,
        weather_tool=weather_tool,
        advisory_tool=advisory_tool,
    )

    auth = AuthContext(
        user_uuid=uuid4(),
        role="FARMER",
        permissions=frozenset([Permission.AGENT_EXECUTE, Permission.WEATHER_READ, Permission.ADVISORY_READ]),
        jti=uuid4(),
    )
    context = ExecutionContext(
        execution_id=uuid4(),
        session_id="session-1",
        auth=auth,
        crop="Paddy",
        district="Warangal",
        state="Telangana",
    )

    result = await agent.execute(
        task="Should I spray my paddy crop tomorrow?",
        context=context,
        parameters={"crop": "Paddy"},
    )

    assert result.status == result.status.COMPLETED
    assert result.grounded is True
    assert len(result.citations) > 0
    assert "recommendation" in result.output


@pytest.mark.asyncio
async def test_scenario_3_market_price_query():
    """SCENARIO 3 — MARKET: Farmer asks 'What is the current price of my crop?'"""
    market_tool = MandiPriceTool()
    res = await market_tool.execute({"commodity": "Paddy", "state": "Telangana", "district": "Warangal"})

    assert res.success is True
    assert res.data["commodity"] == "Paddy"
    assert res.data["modal_price_inr_quintal"] >= res.data["min_price_inr_quintal"]
    assert res.data["msp_inr_quintal"] == 2300.0
    assert res.data["freshness"] == "FRESH"


@pytest.mark.asyncio
async def test_scenario_4_government_scheme_eligibility():
    """SCENARIO 4 — GOVERNMENT SCHEME: Farmer asks 'Which government schemes may apply to me?'"""
    scheme_tool = GovernmentSchemeTool()

    # 1. Broad query
    res_list = await scheme_tool.execute({"state": "Telangana", "crop": "Paddy", "farmer_category": "Small"})
    assert res_list.success is True
    assert res_list.data["schemes_count"] >= 2

    # 2. Specific eligibility evaluation (without fabrication)
    res_eval = await scheme_tool.execute({
        "scheme_id": "TS-RYTHU-BHAROSA",
        "state": "Telangana",
        "crop": "Paddy",
        "landholding_acres": 4.0,
        "farmer_category": "Small",
    })
    assert res_eval.success is True
    assert res_eval.data["evaluation"]["eligibility"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_scenario_5_stale_data_handling():
    """SCENARIO 5 — STALE DATA: Expired observation is explicitly marked as EXPIRED/STALE."""
    service = LiveDataService()

    # Create mock observation that has passed validity
    now = datetime.now(UTC)
    past_validity = now - timedelta(hours=2)

    freshness = service._compute_freshness(past_validity)
    assert freshness == FreshnessStatus.EXPIRED
