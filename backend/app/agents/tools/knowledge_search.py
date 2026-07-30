"""Knowledge search tool backed by the Sprint 3 enterprise retrieval platform."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.contracts.tool import BaseTool, ToolMetadata, ToolResult
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


class KnowledgeSearchTool(BaseTool):
    """Execute knowledge retrieval against the enterprise retrieval pipeline."""

    def __init__(self, pipeline: EnterpriseRetrievalPipeline) -> None:
        metadata = ToolMetadata(
            name="knowledge_search",
            description="Search the enterprise knowledge base for grounded agricultural context.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "crop": {"type": "string"},
                    "state": {"type": "string"},
                    "district": {"type": "string"},
                    "season": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            permissions=["read"],
            timeout_seconds=30.0,
            supported_agent_types=[
                "knowledge_retrieval_agent",
                "crop_advisory_agent",
                "govt_scheme_agent",
                "government_scheme",
                "officer_assistance_agent",
            ],
        )
        super().__init__(metadata)
        self._pipeline = pipeline

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Run a grounded search and return ranked results."""
        t0 = perf_counter()
        query = str(parameters.get("query", ""))
        top_k = int(parameters.get("top_k", 5))

        filters = RetrievalFilters(
            crop=parameters.get("crop"),
            state=parameters.get("state"),
            district=parameters.get("district"),
            season=parameters.get("season"),
        )

        try:
            result = await self._pipeline.search(
                query=query,
                filters=filters,
                top_k=top_k,
                score_threshold=0.25,
                include_delta=True,
            )
            hits = [
                {
                    "chunk_text": item.hit.chunk_text,
                    "score": item.ranking_score,
                    "ranking_score": item.ranking_score,
                    "freshness_score": item.freshness_score,
                    "authority_score": item.authority_score,
                    "answer_context": item.answer_context,
                    "citation": {
                        "title": item.citation.title,
                        "source": item.citation.source,
                        "source_url": item.citation.source_url,
                        "page_number": item.citation.page_number,
                    },
                }
                for item in result.results
            ]
            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data={
                    "query": result.query,
                    "latency_ms": result.latency_ms,
                    "hits": hits,
                    "total_hits": len(hits),
                },
                duration_ms=(perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            logger.error("KnowledgeSearchTool: search failed for query '{}': {}", query, exc)
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={"query": query, "hits": [], "total_hits": 0},
                duration_ms=(perf_counter() - t0) * 1000,
                error_message=str(exc),
            )
