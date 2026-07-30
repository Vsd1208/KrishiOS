"""Factory for constructing a fully wired AgentRuntimeEngine."""

from __future__ import annotations

from functools import lru_cache

from loguru import logger

from app.agents.crop_advisory_agent import CropAdvisoryAgent
from app.agents.govt_scheme_agent import GovtSchemeAgent
from app.agents.officer_agent import OfficerAssistanceAgent
from app.agents.providers.llm import LLMProvider, MockLocalLLMProvider
from app.agents.registry.registry import AgentRegistry
from app.agents.retrieval_agent import KnowledgeRetrievalAgent
from app.agents.runtime.engine import AgentRuntimeEngine
from app.agents.security.guardrails import GuardrailEngine
from app.agents.tools.knowledge_search import KnowledgeSearchTool
from app.agents.tools.registry import ToolRegistry
from app.agents.tools.stubs import (
    CalculatorTool,
    GovernmentDbTool,
    MarketApiTool,
    NotificationServiceTool,
    SpeechModelTool,
    VisionModelTool,
    WeatherApiTool,
)
from app.agents.validation_agent import ResponseValidationAgent
from app.agents.weather_agent import WeatherIntelligenceAgent
from app.retrieval.api.dependencies import get_embedding_provider, get_reranker, get_vector_store
from app.retrieval.citations.builder import CitationBuilder
from app.retrieval.ranking.engine import RankingEngine, RankingWeights
from app.retrieval.retrieval.context import ContextBuilder
from app.retrieval.retrieval.metadata import QueryMetadataExtractor
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


def _build_retrieval_pipeline() -> EnterpriseRetrievalPipeline:
    """Construct the enterprise retrieval pipeline from shared providers."""
    return EnterpriseRetrievalPipeline(
        embedding_provider=get_embedding_provider(),
        vector_store=get_vector_store(),
        reranker=get_reranker(),
        ranking_engine=RankingEngine(RankingWeights()),
        context_builder=ContextBuilder(),
        citation_builder=CitationBuilder(),
        metadata_extractor=QueryMetadataExtractor(),
        live_alias="krishios-live",
        delta_alias="krishios-delta",
    )


def build_runtime_engine(llm_provider: LLMProvider | None = None) -> AgentRuntimeEngine:
    """Create a production AgentRuntimeEngine with all agents and tools registered."""
    llm = llm_provider or MockLocalLLMProvider()
    registry = AgentRegistry()
    tool_registry = ToolRegistry()

    pipeline = _build_retrieval_pipeline()
    knowledge_tool = KnowledgeSearchTool(pipeline)

    weather_tool = WeatherApiTool()
    stub_tools = [
        weather_tool,
        MarketApiTool(),
        GovernmentDbTool(),
        CalculatorTool(),
        VisionModelTool(),
        SpeechModelTool(),
        NotificationServiceTool(),
    ]
    tool_registry.register(knowledge_tool)
    for tool in stub_tools:
        tool_registry.register(tool)

    guardrails = GuardrailEngine()
    agents = [
        KnowledgeRetrievalAgent(knowledge_tool),
        CropAdvisoryAgent(llm, knowledge_tool),
        WeatherIntelligenceAgent(weather_tool),
        GovtSchemeAgent(llm, knowledge_tool),
        OfficerAssistanceAgent(llm),
        ResponseValidationAgent(guardrails),
    ]
    for agent in agents:
        registry.register(agent)

    engine = AgentRuntimeEngine(registry=registry, tool_registry=tool_registry)
    logger.info(
        "AgentRuntimeEngine: initialized with {} agents and {} tools",
        registry.count(),
        tool_registry.count(),
    )
    return engine


@lru_cache(maxsize=1)
def get_runtime_engine() -> AgentRuntimeEngine:
    """Return a process-wide singleton runtime engine."""
    return build_runtime_engine()
