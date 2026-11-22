"""Phase 10c: build the assistant from the configured LLM, the live search index and translation."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.assistant.service import AssistantService, Passage
from app.retrieval.interfaces.types import RetrievalFilters


def pipeline_searcher(pipeline: Any):
    """Adapt the enterprise retrieval pipeline (live + delta index) to the assistant's search."""

    async def search(query_en: str, top_k: int) -> list[Passage]:
        res = await pipeline.search(query_en, RetrievalFilters(), top_k, 0.0, include_delta=True)
        return [Passage(r.hit.chunk_text, r.citation.title, r.citation.page_number,
                        r.citation.source_url, r.hit.similarity) for r in res.results]

    return search


@lru_cache(maxsize=1)
def get_assistant_service() -> AssistantService:
    """One shared assistant: LLM from LLM_PROVIDER (use ``ollama`` for the real local model)."""
    from app.agents.runtime.factory import (  # noqa: PLC0415 - heavy imports, built once
        _build_retrieval_pipeline,
        build_llm_provider,
    )
    from app.translation.service import TranslationService  # noqa: PLC0415

    return AssistantService(build_llm_provider(), pipeline_searcher(_build_retrieval_pipeline()),
                            TranslationService())
