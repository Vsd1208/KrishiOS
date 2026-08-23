"""Fuses vector retrieval with graph retrieval.

Wraps the existing EnterpriseRetrievalPipeline and GraphRetriever,
running them concurrently, and merging the results.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.config.settings import get_settings
from app.graph.interfaces.types import GraphPath, GraphRetrievalResult
from app.graph.retrieval.graph_retriever import GraphRetriever
from app.graph.retrieval.query_extractor import QueryEntityExtractor
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline, RankedRetrievalResult


@dataclass(frozen=True, slots=True)
class HybridContext:
    """The fused context provided to the LLM agent."""
    
    query: str
    document_evidence: list[RankedRetrievalResult]
    graph_evidence: list[GraphPath]
    latency_ms: float


class HybridRAGPipeline:
    """Fuses vector retrieval with graph traversal."""

    def __init__(
        self,
        vector_pipeline: EnterpriseRetrievalPipeline,
        graph_retriever: GraphRetriever,
    ) -> None:
        self._vector_pipeline = vector_pipeline
        self._graph_retriever = graph_retriever
        self._query_extractor = QueryEntityExtractor()
        
        settings = get_settings()
        self._vector_weight = settings.GRAPHRAG_WEIGHT_VECTOR if hasattr(settings, 'GRAPHRAG_WEIGHT_VECTOR') else 0.6
        self._graph_weight = settings.GRAPHRAG_WEIGHT_GRAPH if hasattr(settings, 'GRAPHRAG_WEIGHT_GRAPH') else 0.4

    async def search(
        self,
        query: str,
        filters: RetrievalFilters,
        top_k: int = 10,
        score_threshold: float = 0.3,
        include_delta: bool = True,
    ) -> HybridContext:
        """Execute parallel vector and graph search, then fuse."""
        start = time.perf_counter()
        
        # 1. Extract query entities
        query_entities = await self._query_extractor.extract(query)
        
        # 2. Run in parallel
        vector_task = self._vector_pipeline.search(
            query=query,
            filters=filters,
            top_k=top_k,
            score_threshold=score_threshold,
            include_delta=include_delta,
        )
        graph_task = self._graph_retriever.retrieve_for_entities(query, query_entities)
        
        vector_result, graph_result = await asyncio.gather(vector_task, graph_task)
        
        # 3. Fuse and score (For MVP, we just return both to the LLM context builder)
        # In a fully integrated ranking engine, we would normalize scores here.
        
        latency_ms = (time.perf_counter() - start) * 1000
        
        return HybridContext(
            query=query,
            document_evidence=vector_result.results,
            graph_evidence=graph_result.paths,
            latency_ms=latency_ms,
        )
