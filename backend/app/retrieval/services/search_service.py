"""Application service for enterprise retrieval search."""

from app.retrieval.api.schemas import (
    CitationResponse,
    RetrievalResultResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


class RetrievalSearchService:
    """Use-case service for metadata-aware semantic retrieval."""

    def __init__(self, pipeline: EnterpriseRetrievalPipeline) -> None:
        self._pipeline = pipeline

    async def search(self, request: RetrievalSearchRequest) -> RetrievalSearchResponse:
        """Run enterprise retrieval and serialize the response."""
        filters = RetrievalFilters(**request.filters.model_dump())
        result = await self._pipeline.search(
            query=request.query,
            filters=filters,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            include_delta=request.include_delta,
        )
        return RetrievalSearchResponse(
            query=result.query,
            total_results=len(result.results),
            latency_ms=result.latency_ms,
            results=[
                RetrievalResultResponse(
                    answer_context=item.answer_context,
                    chunk=item.hit.chunk_text,
                    similarity=item.hit.similarity,
                    ranking_score=item.ranking_score,
                    freshness_score=item.freshness_score,
                    authority_score=item.authority_score,
                    document={
                        "id": item.citation.document_id,
                        "title": item.citation.title,
                        "source": item.citation.source,
                        "source_url": item.citation.source_url,
                    },
                    page=item.citation.page_number,
                    chunk_id=item.hit.chunk_id,
                    collection=item.hit.collection,
                    version=self._optional_str(item.hit.metadata.get("index_version")),
                    metadata=item.hit.metadata,
                    citation=CitationResponse(
                        document_id=item.citation.document_id,
                        title=item.citation.title,
                        source=item.citation.source,
                        source_url=item.citation.source_url,
                        page_number=item.citation.page_number,
                        chunk_id=item.citation.chunk_id,
                    ),
                )
                for item in result.results
            ],
        )

    @staticmethod
    def _optional_str(value: object) -> str | None:
        return str(value) if value is not None else None

