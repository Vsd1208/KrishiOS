"""FastAPI dependencies for the Proactive Intelligence module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.providers.llm import MockLocalLLMProvider
from app.agents.runtime.factory import get_runtime_engine
from app.database.session import get_db_session
from app.events.bus import AsyncEventBus, get_event_bus
from app.live_data.services.cache import LiveDataCacheService
from app.live_data.services.live_data_service import LiveDataService
from app.notifications.service import NotificationService
from app.proactive.context import ProactiveContextEngine
from app.proactive.deduplication import EventDeduplicator
from app.proactive.processor import EventProcessor
from app.proactive.review import OfficerReviewService
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.agricultural_rules import RuleRegistry

_deduplicator = EventDeduplicator()
_notification_service = NotificationService(deduplicator=_deduplicator)
_rule_registry = RuleRegistry()
_risk_evaluator = RiskEvaluator()
_officer_review_service = OfficerReviewService()


def get_notification_service() -> NotificationService:
    """Return singleton NotificationService."""
    return _notification_service


def get_officer_review_service() -> OfficerReviewService:
    """Return singleton OfficerReviewService."""
    return _officer_review_service


def get_event_processor(
    session: AsyncSession = Depends(get_db_session),
) -> EventProcessor:
    """Construct EventProcessor per request with the active database session."""
    live_service = LiveDataService(cache_service=LiveDataCacheService())
    
    # Attempt to retrieve graph retriever
    graph_retriever = None
    try:
        from app.graph.api.dependencies import get_graph_store
        from app.graph.retrieval.graph_retriever import GraphRetriever
        store = get_graph_store()
        graph_retriever = GraphRetriever(store)
    except Exception:
        pass

    context_engine = ProactiveContextEngine(
        session=session,
        live_data_service=live_service,
        graph_retriever=graph_retriever,
    )

    runtime_engine = get_runtime_engine()
    proactive_agent = runtime_engine.agents.get("proactive_intelligence_agent")  # type: ignore

    return EventProcessor(
        deduplicator=_deduplicator,
        context_engine=context_engine,
        rule_registry=_rule_registry,
        risk_evaluator=_risk_evaluator,
        notification_service=_notification_service,
        runtime_engine=runtime_engine,
        proactive_agent=proactive_agent,  # type: ignore
    )
