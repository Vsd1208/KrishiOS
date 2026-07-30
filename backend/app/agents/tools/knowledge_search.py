"""Knowledge search tool backed by the Sprint 3 retrieval platform."""

from __future__ import annotations

from app.agents.tools.registry import ToolDefinition
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


class KnowledgeSearchTool:
    """Execute knowledge retrieval against the enterprise retrieval pipeline."""

    def __init__(self, pipeline: EnterpriseRetrievalPipeline) -> None:
        self._pipeline = pipeline
        self.definition = ToolDefinition(
            name="knowledge_search",
            description="Search the enterprise knowledge base for grounded agricultural context.",
            parameters={"query": "string", "top_k": "integer"},
            permissions=["read"],
            timeout_seconds=30,
            retry_policy={"max_retries": 2},
            supported_agents=["knowledge_retrieval", "crop_advisory"],
        )

    async def run(self, query: str, top_k: int = 5) -> dict[str, object]:
        """Run a grounded search and return the ranked results."""
        result = await self._pipeline.search(
            query=query,
            filters=RetrievalFilters(),
            top_k=top_k,
            score_threshold=0.25,
            include_delta=True,
        )
        return {
            "query": result.query,
            "latency_ms": result.latency_ms,
            "results": [
                {
                    "answer_context": item.answer_context,
                    "chunk": item.hit.chunk_text,
                    "ranking_score": item.ranking_score,
                    "freshness_score": item.freshness_score,
                    "authority_score": item.authority_score,
                    "citation": {
                        "title": item.citation.title,
                        "source": item.citation.source,
                        "source_url": item.citation.source_url,
                        "page": item.citation.page_number,
                    },
                }
                for item in result.results
            ],
        }
