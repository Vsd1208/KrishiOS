"""Golden Scenario 2: Disease Risk Evaluation from Microclimate & Knowledge Graph."""

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
async def test_scenario_2_disease_risk_microclimate_pipeline() -> None:
    """Golden Scenario 2: High humidity + Fungal Susceptibility + GraphRAG -> Disease Risk Alert without ungrounded diagnosis."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    context = FarmerFieldContext(
        farmer_id=2,
        farmer_name="Lakshmi Devi",
        phone="9876543211",
        preferred_language="te",
        district_id=12,
        district_name="Warangal",
        state_name="Telangana",
        village="Narsampet",
        landholding_acres=3.5,
        field_id=202,
        field_name="East Chilli Plot",
        soil_type="Red Loam",
        crop_name="Chilli",
        crop_stage="Flowering",
        recent_vision_findings=[{"finding": "minor leaf curling observed", "confidence": 0.78}],
        graph_knowledge_paths=["Chilli -[SUSCEPTIBLE_TO]-> Anthracnose -[FAVORED_BY]-> HighHumidity"],
        vector_rag_snippets=["ICAR-IIHR: Relative humidity exceeding 80% during flowering encourages anthracnose fruit rot in chilli."],
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

    # Event: High humidity detected in Warangal district
    event = EventEnvelope(
        event_type=EventType.HIGH_HUMIDITY,
        payload={
            "district": "Warangal",
            "state": "Telangana",
            "relative_humidity_percent": 88.0,
            "temperature_celsius": 27.5,
            "crop": "Chilli",
        },
        source="Agromet_Station",
    )

    decisions = await processor.process_event(mock_session, event)

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.farmer_id == 2
    assert decision.risk_type == "agronomy.disease_risk"
    assert decision.risk_severity in [RiskSeverity.MEDIUM, RiskSeverity.HIGH]
    assert "Anthracnose" in str(decision.evidence_package["graph_paths"])
    assert len(in_memory_provider.sent_notifications) == 1
