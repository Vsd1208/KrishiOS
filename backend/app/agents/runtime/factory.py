"""Factory for constructing a fully wired AgentRuntimeEngine."""

from __future__ import annotations

from functools import lru_cache

from loguru import logger

from app.agents.crop_advisory_agent import CropAdvisoryAgent
from app.agents.govt_scheme_agent import GovtSchemeAgent
from app.agents.officer_agent import OfficerAssistanceAgent
from app.agents.providers.llm import (
    GeminiLLMProvider,
    LLMProvider,
    MockLocalLLMProvider,
)
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
from app.config.settings import get_settings
from app.retrieval.api.dependencies import (
    get_embedding_provider,
    get_reranker,
    get_vector_store,
)
from app.retrieval.citations.builder import CitationBuilder
from app.retrieval.ranking.engine import RankingEngine, RankingWeights
from app.retrieval.retrieval.context import ContextBuilder
from app.retrieval.retrieval.metadata import QueryMetadataExtractor
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


def _build_retrieval_pipeline() -> EnterpriseRetrievalPipeline:
    """Construct the enterprise retrieval pipeline from shared providers."""

    settings = get_settings()

    return EnterpriseRetrievalPipeline(
        embedding_provider=get_embedding_provider(),
        vector_store=get_vector_store(),
        reranker=get_reranker(),
        ranking_engine=RankingEngine(
            RankingWeights(
                semantic=settings.RANKING_WEIGHT_SEMANTIC,
                authority=settings.RANKING_WEIGHT_AUTHORITY,
                freshness=settings.RANKING_WEIGHT_FRESHNESS,
                crop=settings.RANKING_WEIGHT_CROP,
                state=settings.RANKING_WEIGHT_STATE,
                district=settings.RANKING_WEIGHT_DISTRICT,
                season=settings.RANKING_WEIGHT_SEASON,
                language=settings.RANKING_WEIGHT_LANGUAGE,
            )
        ),
        context_builder=ContextBuilder(),
        citation_builder=CitationBuilder(),
        metadata_extractor=QueryMetadataExtractor(),
        live_alias=settings.RETRIEVAL_LIVE_ALIAS,
        delta_alias=settings.RETRIEVAL_DELTA_ALIAS,
    )


def _build_llm_provider(
    llm_provider: LLMProvider | None = None,
) -> LLMProvider:
    """Build the configured LLM provider."""

    if llm_provider is not None:
        logger.info(
            "LLM provider supplied explicitly | provider={} | model={}",
            llm_provider.provider_name,
            llm_provider.model_name,
        )
        return llm_provider

    settings = get_settings()
    provider_name = settings.LLM_PROVIDER.strip().lower()

    if provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not configured."
            )

        provider = GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.LLM_MODEL,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

        logger.info(
            "LLM provider selected from configuration | provider={} | model={}",
            provider.provider_name,
            provider.model_name,
        )

        return provider

    if provider_name == "local":
        provider = MockLocalLLMProvider(
            model_name=settings.LLM_MODEL
            if settings.LLM_MODEL
            else "krishios-local-v1"
        )

        logger.info(
            "LLM provider selected from configuration | provider={} | model={}",
            provider.provider_name,
            provider.model_name,
        )

        return provider

    raise ValueError(
        f"Unsupported LLM_PROVIDER='{settings.LLM_PROVIDER}'. "
        "Supported providers are: gemini, local."
    )


def build_runtime_engine(
    llm_provider: LLMProvider | None = None,
) -> AgentRuntimeEngine:
    """Create a production AgentRuntimeEngine with all agents and tools registered."""

    llm = _build_llm_provider(llm_provider)

    registry = AgentRegistry()
    tool_registry = ToolRegistry()

    pipeline = _build_retrieval_pipeline()
    knowledge_tool = KnowledgeSearchTool(pipeline)

    from app.agents.tools.graph_knowledge import GraphKnowledgeTool
    from app.graph.api.dependencies import get_graph_store
    from app.graph.fusion.hybrid_pipeline import HybridRAGPipeline
    from app.graph.retrieval.graph_retriever import GraphRetriever

    try:
        graph_store = get_graph_store()
        graph_retriever = GraphRetriever(graph_store)
        hybrid_pipeline = HybridRAGPipeline(pipeline, graph_retriever)
        graph_tool = GraphKnowledgeTool(hybrid_pipeline)
    except Exception:
        logger.warning(
            "GraphRAG unavailable during runtime construction; "
            "falling back to vector knowledge search."
        )
        graph_tool = None

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

    if graph_tool:
        tool_registry.register(graph_tool)

    for tool in stub_tools:
        tool_registry.register(tool)

    from app.agents.proactive_agent import ProactiveIntelligenceAgent

    guardrails = GuardrailEngine()

    agents = [
        KnowledgeRetrievalAgent(knowledge_tool),
        CropAdvisoryAgent(llm, graph_tool or knowledge_tool),
        WeatherIntelligenceAgent(weather_tool),
        GovtSchemeAgent(llm, graph_tool or knowledge_tool),
        OfficerAssistanceAgent(llm),
        ResponseValidationAgent(guardrails),
        ProactiveIntelligenceAgent(llm),
    ]

    for agent in agents:
        registry.register(agent)

    engine = AgentRuntimeEngine(
        registry=registry,
        tool_registry=tool_registry,
    )

    logger.info(
        "AgentRuntimeEngine initialized | agents={} | tools={} | "
        "llm_provider={} | llm_model={}",
        registry.count(),
        tool_registry.count(),
        llm.provider_name,
        llm.model_name,
    )

    return engine


@lru_cache(maxsize=1)
def get_runtime_engine() -> AgentRuntimeEngine:
    """Return a process-wide singleton runtime engine."""

    return build_runtime_engine()