"""Knowledge search tool backed by the Sprint 3 enterprise retrieval platform.

The tool performs grounded semantic retrieval with progressive metadata
relaxation. Specific geographic metadata is preferred when available, but
authoritative documents that are not tagged with district/state metadata must
remain retrievable.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.contracts.tool import BaseTool, ToolMetadata, ToolResult
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline


@dataclass(frozen=True, slots=True)
class _SearchAttempt:
    """Metadata configuration used for one retrieval attempt."""

    name: str
    filters: RetrievalFilters


class KnowledgeSearchTool(BaseTool):
    """Execute grounded search against the enterprise retrieval pipeline."""

    def __init__(self, pipeline: EnterpriseRetrievalPipeline) -> None:
        metadata = ToolMetadata(
            name="knowledge_search",
            description=(
                "Search the enterprise knowledge base for grounded agricultural "
                "context using semantic retrieval and metadata-aware filtering."
            ),
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
        """Run a grounded search with progressive metadata relaxation."""

        started = perf_counter()

        query = self._normalize_text(parameters.get("query"))
        top_k = self._normalize_top_k(parameters.get("top_k", 5))

        crop = self._normalize_text(parameters.get("crop"))
        state = self._normalize_text(parameters.get("state"))
        district = self._normalize_text(parameters.get("district"))
        season = self._normalize_text(parameters.get("season"))

        if not query:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={
                    "query": "",
                    "hits": [],
                    "total_hits": 0,
                },
                duration_ms=(perf_counter() - started) * 1000,
                error_message="Knowledge search query cannot be empty.",
            )

        attempts = self._build_search_attempts(
            crop=crop,
            state=state,
            district=district,
            season=season,
        )

        logger.info(
            "KNOWLEDGE SEARCH INPUT | "
            "query='{}' | crop={} | state={} | district={} | "
            "season={} | top_k={} | attempts={}",
            query,
            crop,
            state,
            district,
            season,
            top_k,
            len(attempts),
        )

        last_latency_ms = 0.0

        try:
            for index, attempt in enumerate(attempts, start=1):
                logger.info(
                    "KNOWLEDGE SEARCH ATTEMPT | "
                    "attempt={}/{} | strategy={} | "
                    "crop={} | state={} | district={} | season={}",
                    index,
                    len(attempts),
                    attempt.name,
                    attempt.filters.crop,
                    attempt.filters.state,
                    attempt.filters.district,
                    attempt.filters.season,
                )

                result = await self._pipeline.search(
                    query=query,
                    filters=attempt.filters,
                    top_k=top_k,
                    score_threshold=0.25,
                    include_delta=True,
                )

                last_latency_ms = result.latency_ms

                logger.info(
                    "KNOWLEDGE SEARCH ATTEMPT OUTPUT | "
                    "strategy={} | results={} | latency_ms={}",
                    attempt.name,
                    len(result.results),
                    result.latency_ms,
                )

                if result.results:
                    hits = self._serialize_results(result.results)

                    logger.info(
                        "KNOWLEDGE SEARCH SUCCESS | "
                        "strategy={} | query='{}' | hits={}",
                        attempt.name,
                        query,
                        len(hits),
                    )

                    return ToolResult(
                        tool_name=self.metadata.name,
                        success=True,
                        data={
                            "query": result.query,
                            "latency_ms": result.latency_ms,
                            "hits": hits,
                            "total_hits": len(hits),
                            "retrieval_strategy": attempt.name,
                            "metadata_relaxed": index > 1,
                        },
                        duration_ms=(perf_counter() - started) * 1000,
                    )

            logger.warning(
                "KNOWLEDGE SEARCH NO RESULTS | "
                "query='{}' | strategies_tried={}",
                query,
                [attempt.name for attempt in attempts],
            )

            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data={
                    "query": query,
                    "latency_ms": last_latency_ms,
                    "hits": [],
                    "total_hits": 0,
                    "retrieval_strategy": "no_results",
                    "metadata_relaxed": bool(attempts),
                },
                duration_ms=(perf_counter() - started) * 1000,
            )

        except Exception as exc:
            logger.exception(
                "KnowledgeSearchTool: search failed for query '{}'",
                query,
            )

            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={
                    "query": query,
                    "hits": [],
                    "total_hits": 0,
                },
                duration_ms=(perf_counter() - started) * 1000,
                error_message=str(exc),
            )

    @classmethod
    def _build_search_attempts(
        cls,
        *,
        crop: str | None,
        state: str | None,
        district: str | None,
        season: str | None,
    ) -> list[_SearchAttempt]:
        """Build progressively broader retrieval strategies.

        The ordering intentionally starts with the most specific context and
        relaxes only geographic metadata. Crop and season remain the primary
        agricultural relevance constraints whenever they are available.
        """

        attempts: list[_SearchAttempt] = []
        seen: set[tuple[str | None, str | None, str | None, str | None]] = set()

        def add_attempt(
            name: str,
            *,
            attempt_crop: str | None,
            attempt_state: str | None,
            attempt_district: str | None,
            attempt_season: str | None,
        ) -> None:
            key = (
                attempt_crop,
                attempt_state,
                attempt_district,
                attempt_season,
            )

            if key in seen:
                return

            seen.add(key)

            attempts.append(
                _SearchAttempt(
                    name=name,
                    filters=RetrievalFilters(
                        crop=attempt_crop,
                        state=attempt_state,
                        district=attempt_district,
                        season=attempt_season,
                    ),
                )
            )

        # ---------------------------------------------------------
        # Attempt 1 — full farmer context
        # ---------------------------------------------------------
        add_attempt(
            "full_context",
            attempt_crop=crop,
            attempt_state=state,
            attempt_district=district,
            attempt_season=season,
        )

        # ---------------------------------------------------------
        # Attempt 2 — remove district
        #
        # Useful for authoritative state/national documents that contain
        # state/crop/season metadata but are not district-specific.
        # ---------------------------------------------------------
        if district:
            add_attempt(
                "without_district",
                attempt_crop=crop,
                attempt_state=state,
                attempt_district=None,
                attempt_season=season,
            )

        # ---------------------------------------------------------
        # Attempt 3 — remove state as well
        #
        # This is important for ICAR/TNAU-style documents that are
        # agricultural/crop-specific but do not carry geographic payload
        # metadata.
        # ---------------------------------------------------------
        if state:
            add_attempt(
                "crop_season",
                attempt_crop=crop,
                attempt_state=None,
                attempt_district=None,
                attempt_season=season,
            )

        # ---------------------------------------------------------
        # Attempt 4 — crop only
        #
        # Last controlled fallback when the season metadata is also absent
        # or inconsistent in an authoritative document.
        # ---------------------------------------------------------
        if season:
            add_attempt(
                "crop_only",
                attempt_crop=crop,
                attempt_state=None,
                attempt_district=None,
                attempt_season=None,
            )

        # ---------------------------------------------------------
        # Final semantic fallback
        #
        # Only used when no crop was available at all.
        # ---------------------------------------------------------
        if crop is None:
            add_attempt(
                "semantic_only",
                attempt_crop=None,
                attempt_state=None,
                attempt_district=None,
                attempt_season=None,
            )

        return attempts

    @staticmethod
    def _serialize_results(results: list[Any]) -> list[dict[str, Any]]:
        """Convert ranked retrieval results into the agent tool contract."""

        hits: list[dict[str, Any]] = []

        for item in results:
            citation = item.citation

            hits.append(
                {
                    "chunk_text": item.hit.chunk_text,
                    "score": item.ranking_score,
                    "ranking_score": item.ranking_score,
                    "similarity": item.hit.similarity,
                    "freshness_score": item.freshness_score,
                    "authority_score": item.authority_score,
                    "answer_context": item.answer_context,
                    "metadata": dict(item.hit.metadata),
                    "citation": {
                        "title": citation.title,
                        "source": citation.source,
                        "source_url": citation.source_url,
                        "page_number": citation.page_number,
                    },
                }
            )

        return hits

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        """Normalize optional metadata for case-insensitive corpus matching."""

        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        return text.casefold()

    @staticmethod
    def _normalize_top_k(value: Any) -> int:
        """Normalize top-k while preventing invalid retrieval limits."""

        try:
            top_k = int(value)
        except (TypeError, ValueError):
            top_k = 5

        return max(1, min(top_k, 20))