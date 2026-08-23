"""Golden Scenario 1: Proactive Heavy Rain Advisory on Paddy."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.agents.providers.llm import MockLocalLLMProvider
from app.agents.proactive_agent import ProactiveIntelligenceAgent
from app.events.contracts import EventEnvelope, EventType
from app.models.proactive import AlertPriority, AlertStatus, RiskSeverity
from app.notifications.providers import InMemoryNotificationProvider
from app.notifications.service import NotificationService
from app.proactive.context import FarmerFieldContext, ProactiveContextEngine
from app.proactive.deduplication import EventDeduplicator
from app.proactive.processor import EventProcessor
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.agricultural_rules import RuleRegistry


@pytest.mark.asyncio
async def test_scenario_1_heavy_rain_advisory_pipeline() -> None:
    """Golden Scenario 1: Heavy rain forecast -> Context Collection -> Rule Match -> Risk -> Proactive Agent -> Notification."""
    # 1. Setup mock session and context
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    context = FarmerFieldContext(
        farmer_id=1,
        farmer_name="Ramesh Reddy",
        phone="9876543210",
        preferred_language="te",
        district_id=10,
        district_name="Nizamabad",
        state_name="Telangana",
        village="Armoor",
        landholding_acres=5.0,
        field_id=101,
        field_name="North Field",
        soil_type="Black Clay",
        crop_name="Paddy",
        crop_stage="Tillering",
        live_weather={"precipitation_sum_mm": 85.0},
        vector_rag_snippets=["PJTSAU: Ensure drainage in paddy tillering stage to avoid submergence."],
        graph_knowledge_paths=["Paddy -[HAS_GROWTH_STAGE]-> Tillering -[SUSCEPTIBLE_TO]-> Waterlogging"],
    )

    mock_context_engine = AsyncMock(spec=ProactiveContextEngine)
    mock_context_engine.collect_contexts_for_event = AsyncMock(return_value=[context])

    # 2. Setup services
    dedup = EventDeduplicator()
    in_memory_provider = InMemoryNotificationProvider()
    notif_service = NotificationService(
        deduplicator=dedup,
        providers={"IN_APP": in_memory_provider, "SMS": in_memory_provider},
    )
    # Stub preference
    notif_service._get_or_create_preferences = AsyncMock(
        return_value=MagicMock(
            preferred_channel="IN_APP",
            preferred_language="te",
            quiet_hours_enabled=False,
            enable_weather_alerts=True,
            enable_disease_alerts=True,
            enable_market_alerts=True,
            enable_scheme_alerts=True,
        )
    )

    proactive_agent = ProactiveIntelligenceAgent(MockLocalLLMProvider())
    rule_registry = RuleRegistry()
    risk_evaluator = RiskEvaluator()

    processor = EventProcessor(
        deduplicator=dedup,
        context_engine=mock_context_engine,
        rule_registry=rule_registry,
        risk_evaluator=risk_evaluator,
        notification_service=notif_service,
        proactive_agent=proactive_agent,
    )

    # 3. Simulate Incoming Weather Event
    event = EventEnvelope(
        event_type=EventType.HEAVY_RAIN_EXPECTED,
        payload={
            "district": "Nizamabad",
            "state": "Telangana",
            "rainfall_mm": 85.0,
            "probability": 0.92,
            "forecast_date": "2026-08-23",
        },
        source="IMD_Sync",
    )

    decisions = await processor.process_event(mock_session, event)

    # 4. Assertions
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.farmer_id == 1
    assert decision.field_id == 101
    assert decision.risk_type == "weather.heavy_rainfall"
    assert decision.risk_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]
    assert decision.confidence >= 0.85
    assert len(decision.evidence_package["active_rules"]) > 0
    assert len(decision.evidence_package["rag_citations"]) > 0

    # Verify notification was queued/sent
    assert len(in_memory_provider.sent_notifications) == 1
    sent_notif = in_memory_provider.sent_notifications[0]
    assert sent_notif.farmer_id == 1
    assert "Agricultural Alert" in sent_notif.title
