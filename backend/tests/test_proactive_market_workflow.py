"""Golden Scenario 3: Proactive Market Price Movement Alert."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.providers.llm import MockLocalLLMProvider
from app.agents.proactive_agent import ProactiveIntelligenceAgent
from app.events.contracts import EventEnvelope, EventType
from app.models.proactive import RiskSeverity
from app.notifications.providers import InMemoryNotificationProvider
from app.notifications.service import NotificationService
from app.proactive.context import FarmerFieldContext, ProactiveContextEngine
from app.proactive.deduplication import EventDeduplicator
from app.proactive.processor import EventProcessor
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.agricultural_rules import RuleRegistry


@pytest.mark.asyncio
async def test_scenario_3_market_price_drop_pipeline() -> None:
    """Golden Scenario 3: Significant price drop (-18%) for Tomato -> Farmer Alert without speculation."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    context = FarmerFieldContext(
        farmer_id=3,
        farmer_name="Srinivas Rao",
        phone="9876543212",
        preferred_language="te",
        district_id=14,
        district_name="Khammam",
        state_name="Telangana",
        village="Madhira",
        landholding_acres=2.0,
        field_id=303,
        field_name="Tomato Patch",
        crop_name="Tomato",
        crop_stage="Harvested",
    )

    mock_context_engine = AsyncMock(spec=ProactiveContextEngine)
    mock_context_engine.collect_contexts_for_event = AsyncMock(return_value=[context])

    dedup = EventDeduplicator()
    in_memory_provider = InMemoryNotificationProvider()
    notif_service = NotificationService(
        deduplicator=dedup,
        providers={"IN_APP": in_memory_provider, "SMS": in_memory_provider},
    )
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

    event = EventEnvelope(
        event_type=EventType.MARKET_PRICE_CHANGED,
        payload={
            "commodity": "Tomato",
            "market": "Khammam Mandi",
            "current_price": 1650.0,
            "previous_price": 2020.0,
            "change_percent": -18.3,
            "district": "Khammam",
            "state": "Telangana",
        },
        source="Agmarknet_Sync",
    )

    decisions = await processor.process_event(mock_session, event)

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.farmer_id == 3
    assert decision.risk_type == "market.price_volatility"
    assert decision.risk_severity in [RiskSeverity.MEDIUM, RiskSeverity.HIGH]
    assert decision.evidence_package["live_telemetry"]["event_payload"]["commodity"] == "Tomato"
    assert len(in_memory_provider.sent_notifications) == 1
    sent_notif = in_memory_provider.sent_notifications[0]
    assert "Market" in sent_notif.title
    assert "Tomato" in sent_notif.topic_key
