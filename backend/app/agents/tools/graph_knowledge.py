"""Graph Knowledge tool for Agent Runtime.

Provides agents with GraphRAG access without exposing raw Cypher.
Agents provide a query, and the tool returns a fused vector+graph result.
"""

from typing import Any

from loguru import logger

from app.agents.contracts.tool import BaseTool, ToolMetadata, ToolResult
from app.auth.permissions import Permission
from app.graph.fusion.hybrid_pipeline import HybridRAGPipeline
from app.retrieval.interfaces.types import RetrievalFilters


class GraphKnowledgeTool(BaseTool):
    """Tool for querying the agricultural knowledge graph and vector store."""

    def __init__(self, pipeline: HybridRAGPipeline) -> None:
        self._pipeline = pipeline
        self._metadata = ToolMetadata(
            name="knowledge_graph_search",
            description=(
                "Search the KrishiOS knowledge base using hybrid graph-vector retrieval. "
                "Use this to find relationships between crops, diseases, pests, treatments, "
                "and to retrieve authoritative text snippets. Do not use this for raw DB queries."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g., 'What diseases affect Paddy in kharif?'",
                    },
                    "crop": {
                        "type": "string",
                        "description": "Optional crop filter.",
                    },
                    "season": {
                        "type": "string",
                        "description": "Optional season filter (e.g., 'kharif', 'rabi').",
                    },
                },
                "required": ["query"],
            },
            required_permission=Permission.GRAPH_READ,
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the hybrid search."""
        query = kwargs.get("query")
        if not query or not isinstance(query, str):
            return ToolResult(
                success=False,
                output="Missing or invalid 'query' parameter.",
                error="Invalid parameters",
            )

        crop = kwargs.get("crop")
        season = kwargs.get("season")
        
        filters = RetrievalFilters()
        if crop:
            filters.crop = crop
        if season:
            filters.season = season

        try:
            logger.info("GraphKnowledgeTool executing for query: '{}'", query)
            context = await self._pipeline.search(query, filters)
            
            # Format the output for the LLM
            output_parts = [f"Hybrid Search Results for: {query}"]
            output_parts.append(f"Latency: {context.latency_ms:.1f}ms\n")
            
            output_parts.append("--- GRAPH EVIDENCE (Relationships) ---")
            if not context.graph_evidence:
                output_parts.append("No direct graph relationships found.")
            for path in context.graph_evidence:
                output_parts.append(f"- {path.path_text} (relevance: {path.relevance_score:.2f})")
                
            output_parts.append("\n--- TEXT EVIDENCE (Vector Search) ---")
            if not context.document_evidence:
                output_parts.append("No text evidence found.")
            for i, hit in enumerate(context.document_evidence):
                # Ensure hit is RankedRetrievalResult
                output_parts.append(f"[Source {i+1}] {hit.answer_context}")

            return ToolResult(
                success=True,
                output="\n".join(output_parts),
                data={
                    "latency_ms": context.latency_ms,
                    "graph_paths_count": len(context.graph_evidence),
                    "vector_hits_count": len(context.document_evidence),
                },
            )
        except Exception as exc:
            logger.exception("GraphKnowledgeTool failed: {}", exc)
            return ToolResult(
                success=False,
                output=f"Search failed: {exc}",
                error=str(exc),
            )
