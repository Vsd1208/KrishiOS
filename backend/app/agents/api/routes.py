"""HTTP routes for agent runtime execution and discovery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.agents.api.schemas import AgentExecutionRequest, AgentExecutionResponse
from app.agents.runtime.runtime import AgentRuntime
from app.agents.registry.registry import AgentRegistry
from app.agents.tools.registry import ToolRegistry
from app.agents.agents.knowledge_retrieval import KnowledgeRetrievalAgent
from app.agents.agents.crop_advisory import CropAdvisoryAgent
from app.agents.agents.weather_intelligence import WeatherIntelligenceAgent
from app.agents.agents.government_scheme import GovernmentSchemeAgent
from app.agents.agents.officer_assistance import OfficerAssistanceAgent
from app.agents.agents.response_validation import ResponseValidationAgent
from app.retrieval.api.dependencies import get_embedding_provider, get_vector_store, get_reranker
from app.retrieval.ranking.engine import RankingEngine, RankingWeights
from app.retrieval.retrieval.context import ContextBuilder
from app.retrieval.retrieval.metadata import QueryMetadataExtractor
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline
from app.retrieval.citations.builder import CitationBuilder
from app.agents.tools.knowledge_search import KnowledgeSearchTool

router = APIRouter(tags=["Agent Runtime"])


def _build_runtime() -> AgentRuntime:
    """Create a runtime instance with the base agent set and tool registry."""
    registry = AgentRegistry()
    tool_registry = ToolRegistry()

    pipeline = EnterpriseRetrievalPipeline(
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
    knowledge_tool = KnowledgeSearchTool(pipeline)
    tool_registry.register(knowledge_tool.definition)

    agents = [
        KnowledgeRetrievalAgent(knowledge_tool),
        CropAdvisoryAgent(),
        WeatherIntelligenceAgent(),
        GovernmentSchemeAgent(),
        OfficerAssistanceAgent(),
        ResponseValidationAgent(),
    ]
    for agent in agents:
        registry.register(agent, agent.metadata())

    runtime = AgentRuntime(registry=registry, tool_registry=tool_registry)
    return runtime


@router.post("/agents/execute", response_model=AgentExecutionResponse, status_code=status.HTTP_200_OK)
async def execute_agent(request: AgentExecutionRequest) -> AgentExecutionResponse:
    """Execute the agent runtime for a user goal."""
    runtime = _build_runtime()
    results = await runtime.execute(request.goal, request.session_id)
    return AgentExecutionResponse(
        goal=request.goal,
        status="completed",
        results=[{"agent": item.agent_name, "status": item.status, "output": item.output} for item in results],
    )


@router.get("/agents", status_code=status.HTTP_200_OK)
async def list_agents() -> list[dict[str, object]]:
    """List registered agents."""
    runtime = _build_runtime()
    return [
        {
            "name": metadata.name,
            "description": metadata.description,
            "capabilities": metadata.capabilities,
            "priority": metadata.priority,
            "version": metadata.version,
            "health_status": metadata.health_status,
        }
        for _, metadata in runtime.registry().list()
    ]


@router.get("/runtime/status", status_code=status.HTTP_200_OK)
async def runtime_status() -> dict[str, object]:
    """Return a lightweight runtime status summary."""
    return {"status": "healthy", "registered_agents": len(_build_runtime().registry().list())}
