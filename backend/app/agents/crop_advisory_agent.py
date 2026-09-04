"""Crop Advisory Agent for agronomic guidance, pest control, and soil recommendations."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import (
    AgentStatus,
    AgentStepTrace,
    ExecutionContext,
    ExecutionResult,
)
from app.agents.providers.llm import LLMProvider
from app.agents.tools.knowledge_search import KnowledgeSearchTool
from app.agents.tools.live_advisory import LiveAdvisoryTool
from app.agents.tools.live_weather import LiveWeatherTool


class CropAdvisoryAgent(BaseAgent):
    """Production Crop Advisory Agent for Indian agriculture."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        search_tool: KnowledgeSearchTool,
        weather_tool: LiveWeatherTool | None = None,
        advisory_tool: LiveAdvisoryTool | None = None,
    ) -> None:
        metadata = AgentMetadata(
            name="crop_advisory_agent",
            description=(
                "Provides grounded crop advisories, disease identification "
                "guidance, and fertilizer schedules."
            ),
            capabilities=[
                "advisory",
                "crop_health",
                "fertilizer",
                "pest_control",
                "weather_spray_decision",
            ],
            input_schema={
                "query": "string",
                "crop": "string",
            },
            output_schema={
                "recommendation": "string",
                "citations": "list",
            },
            supported_tools=[
                "knowledge_search",
                "calculator",
                "live_weather",
                "live_advisory",
            ],
            priority=20,
            version="1.2.0",
        )

        super().__init__(metadata)

        self._llm = llm_provider
        self._search_tool = search_tool
        self._weather_tool = weather_tool
        self._advisory_tool = advisory_tool

    async def initialize(self) -> None:
        """Initialize the agent."""
        self._status = AgentStatus.IDLE
        logger.info("CropAdvisoryAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Generate grounded agricultural advice."""

        started = perf_counter()
        self._status = AgentStatus.RUNNING

        params = parameters or {}

        crop = self._get_string_parameter(
            params,
            "crop",
        ) or context.crop or "crop"

        district = self._get_string_parameter(
            params,
            "district",
        ) or context.district

        state = self._get_string_parameter(
            params,
            "state",
        ) or context.state

        # ============================================================
        # 1. USE UPSTREAM VERIFIED RETRIEVAL CONTEXT
        # ============================================================
        #
        # The orchestrator passes the output of
        # knowledge_retrieval_agent as "retrieval_context".
        #
        # This prevents the advisory agent from performing an
        # independent search and losing the verified retrieval chain.
        #
        retrieval_context = params.get(
            "retrieval_context"
        )

        hits = self._extract_retrieval_hits(
            retrieval_context
        )

        # If the orchestrator did not provide retrieval context,
        # retain the previous fallback behavior and search directly.
        if not hits:
            hits = await self._fallback_knowledge_search(
                task=task,
                crop=crop,
                state=state,
                season=context.season,
            )

        context_str = self._build_knowledge_context(
            hits
        )

        citations = self._extract_citations(
            hits
        )

        # ============================================================
        # 2. LIVE WEATHER / OFFICIAL ADVISORY
        # ============================================================

        live_telemetry_str = ""

        weather_data: dict[str, Any] | None = None
        advisory_data: dict[str, Any] | None = None

        weather_keywords = (
            "spray",
            "weather",
            "rain",
            "tomorrow",
            "forecast",
            "humidity",
        )

        if (
            self._weather_tool is not None
            and any(
                keyword in task.casefold()
                for keyword in weather_keywords
            )
        ):
            weather_result = await self._weather_tool.execute(
                {
                    "district": district,
                    "state": state,
                    "forecast_days": 3,
                }
            )

            if weather_result.success:
                weather_data = self._as_dict(
                    weather_result.data
                )

                current = self._as_dict(
                    weather_data.get("current")
                )

                forecast = self._as_dict(
                    weather_data.get("forecast")
                )

                live_telemetry_str += (
                    "\n[LIVE WEATHER TELEMETRY]\n"
                    f"Temperature: "
                    f"{current.get('temperature_celsius')}°C, "
                    f"Humidity: "
                    f"{current.get('relative_humidity_percent')}%, "
                    f"Wind Speed: "
                    f"{current.get('wind_speed_mps')} m/s, "
                    f"Condition: "
                    f"{current.get('condition')}\n"
                    f"Spray Window Favorable: "
                    f"{forecast.get('spray_window_favorable')} "
                    f"({forecast.get('spray_window_reason')})\n"
                    f"Forecast: "
                    f"{forecast.get('summary')}\n"
                    f"Source: "
                    f"{current.get('source')} "
                    f"(Observed: "
                    f"{current.get('observed_at')})\n"
                )

        if self._advisory_tool is not None and crop:
            advisory_result = await self._advisory_tool.execute(
                {
                    "crop": crop,
                    "district": district,
                    "state": state,
                }
            )

            if (
                advisory_result.success
                and isinstance(advisory_result.data, dict)
                and "content" in advisory_result.data
            ):
                advisory_data = advisory_result.data

                live_telemetry_str += (
                    "\n[OFFICIAL AGROMET ADVISORY]\n"
                    f"Title: "
                    f"{advisory_data.get('title')}\n"
                    f"Advisory: "
                    f"{advisory_data.get('content')}\n"
                    f"Issuing Authority: "
                    f"{advisory_data.get('issuing_authority')}\n"
                )

        # ============================================================
        # 3. BUILD GROUNDED LLM PROMPT
        # ============================================================

        prompt = (
            f"User Query: {task}\n"
            f"Crop: {crop}, "
            f"Region: {district or 'India'}, "
            f"State: {state or 'India'}, "
            f"Season: {context.season or 'General'}\n"
            f"{live_telemetry_str}\n"
            "\n"
            "Verified ICAR/Department Knowledge Base and Graph:\n"
            f"{context_str}\n\n"
            "Instructions:\n"
            "1. Use the verified knowledge context above as the "
            "primary source for agronomic facts.\n"
            "2. Do not invent facts, pests, diseases, treatments, "
            "dosages, or recommendations that are unsupported by "
            "the verified context.\n"
            "3. Give practical and understandable guidance to the "
            "farmer.\n"
            "4. Clearly distinguish verified agronomic knowledge "
            "from live weather or advisory information.\n"
            "5. If the verified context does not contain enough "
            "information to answer the question safely, explicitly "
            "say that more verified information is required.\n"
        )

        llm_response = await self._llm.generate(
            prompt=prompt,
            system_instruction=(
                "You are an expert ICAR agronomist giving precise "
                "and safe guidance to Indian farmers. "
                "Ground factual claims in the supplied verified "
                "knowledge context."
            ),
        )

        # ============================================================
        # 4. TRACE
        # ============================================================

        duration_ms = (
            perf_counter() - started
        ) * 1000

        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="synthesize_advisory",
            input_data={
                "task": task,
                "crop": crop,
                "retrieval_context_provided": isinstance(
                    retrieval_context,
                    dict,
                ),
            },
            output_data={
                "tokens": llm_response.total_tokens,
                "hits_used": len(hits),
                "citations_used": len(citations),
            },
            duration_ms=duration_ms,
        )

        context.add_trace(trace)

        # ============================================================
        # 5. CONFIDENCE / GROUNDING
        # ============================================================

        confidence = self._calculate_confidence(
            hits
        )

        grounded = len(hits) > 0

        self._status = AgentStatus.COMPLETED

        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "recommendation": llm_response.content,
                "crop": crop,
                "context_used": grounded,
            },
            confidence_score=confidence,
            grounded=grounded,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    # ================================================================
    # RETRIEVAL HELPERS
    # ================================================================

    @staticmethod
    def _extract_retrieval_hits(
        retrieval_context: Any,
    ) -> list[dict[str, Any]]:
        """Extract valid retrieval hits from upstream agent output."""

        if not isinstance(
            retrieval_context,
            dict,
        ):
            return []

        raw_hits = retrieval_context.get(
            "hits"
        )

        if not isinstance(
            raw_hits,
            list,
        ):
            return []

        return [
            hit
            for hit in raw_hits
            if isinstance(hit, dict)
        ]

    async def _fallback_knowledge_search(
        self,
        task: str,
        crop: str,
        state: str | None,
        season: str | None,
    ) -> list[dict[str, Any]]:
        """Fallback search when no upstream retrieval context exists."""

        try:
            search_result = await self._search_tool.execute(
                {
                    "query": task,
                    "crop": crop,
                    "state": state,
                    "season": season,
                    "top_k": 3,
                }
            )
        except Exception as exc:
            logger.exception(
                "CropAdvisoryAgent: fallback knowledge search failed: {}",
                exc,
            )
            return []

        raw_hits = search_result.data.get(
            "hits",
            [],
        )

        if not isinstance(
            raw_hits,
            list,
        ):
            return []

        return [
            hit
            for hit in raw_hits
            if isinstance(hit, dict)
        ]

    @staticmethod
    def _build_knowledge_context(
        hits: list[dict[str, Any]],
    ) -> str:
        """Build the verified knowledge context supplied to the LLM."""

        chunks = [
            str(hit.get("chunk_text", "")).strip()
            for hit in hits
            if hit.get("chunk_text")
        ]

        if not chunks:
            return (
                "[No verified knowledge context was retrieved.]"
            )

        return "\n---\n".join(chunks)

    @staticmethod
    def _extract_citations(
        hits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract valid citation objects from retrieval hits."""

        citations: list[dict[str, Any]] = []

        for hit in hits:
            citation = hit.get(
                "citation"
            )

            if isinstance(
                citation,
                dict,
            ):
                citations.append(citation)

        return citations

    @staticmethod
    def _calculate_confidence(
        hits: list[dict[str, Any]],
    ) -> float:
        """Calculate confidence from the strongest retrieved hit."""

        if not hits:
            return 0.5

        score = hits[0].get(
            "score",
            0.7,
        )

        try:
            return float(score)
        except (
            TypeError,
            ValueError,
        ):
            return 0.7

    # ================================================================
    # TYPE-SAFE VALUE HELPERS
    # ================================================================

    @staticmethod
    def _get_string_parameter(
        parameters: dict[str, Any],
        key: str,
    ) -> str | None:
        """Read a string parameter safely."""

        value = parameters.get(key)

        if isinstance(
            value,
            str,
        ):
            return value

        return None

    @staticmethod
    def _as_dict(
        value: Any,
    ) -> dict[str, Any]:
        """Convert an arbitrary value to a dictionary safely."""

        if isinstance(
            value,
            dict,
        ):
            return value

        return {}

    # ================================================================
    # LIFECYCLE
    # ================================================================

    async def validate(
        self,
        result: ExecutionResult,
    ) -> bool:
        """Validate the advisory execution result."""

        return (
            result.status
            == AgentStatus.COMPLETED
            and result.confidence_score >= 0.3
        )

    async def cleanup(self) -> None:
        """Reset agent state."""

        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        """Return agent health information."""

        return {
            "status": "healthy",
            "agent": self.metadata.name,
            "llm": self._llm.provider_name,
        }