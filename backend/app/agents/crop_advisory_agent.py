"""Crop Advisory Agent for agronomic guidance, pest control, and soil recommendations."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
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
            description="Provides grounded crop advisories, disease identification guidance, and fertilizer schedules.",
            capabilities=["advisory", "crop_health", "fertilizer", "pest_control", "weather_spray_decision"],
            input_schema={"query": "string", "crop": "string"},
            output_schema={"recommendation": "string", "citations": "list"},
            supported_tools=["knowledge_search", "calculator", "live_weather", "live_advisory"],
            priority=20,
            version="1.1.0",
        )
        super().__init__(metadata)
        self._llm = llm_provider
        self._search_tool = search_tool
        self._weather_tool = weather_tool
        self._advisory_tool = advisory_tool

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("CropAdvisoryAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        params = parameters or {}
        crop = params.get("crop") or context.crop or "crop"
        district = params.get("district") or context.district
        state = params.get("state") or context.state

        # 1. Search verified knowledge base
        search_res = await self._search_tool.execute({
            "query": task,
            "crop": crop,
            "state": state,
            "season": context.season,
            "top_k": 3,
        })

        hits = search_res.data.get("hits", [])
        context_str = "\n---\n".join([h.get("chunk_text", "") for h in hits])
        citations = [h.get("citation") for h in hits if h.get("citation")]

        # 2. Check if live weather or advisory tool should be queried (e.g. spray, weather, rain in task)
        live_telemetry_str = ""
        weather_data = None
        advisory_data = None

        if self._weather_tool is not None and any(w in task.lower() for w in ["spray", "weather", "rain", "tomorrow", "forecast", "humidity"]):
            w_res = await self._weather_tool.execute({"district": district, "state": state, "forecast_days": 3})
            if w_res.success:
                weather_data = w_res.data
                curr = weather_data.get("current", {})
                fc = weather_data.get("forecast", {})
                live_telemetry_str += (
                    f"\n[LIVE WEATHER TELEMETRY]\n"
                    f"Temperature: {curr.get('temperature_celsius')}°C, Humidity: {curr.get('relative_humidity_percent')}%, "
                    f"Wind Speed: {curr.get('wind_speed_mps')} m/s, Condition: {curr.get('condition')}\n"
                    f"Spray Window Favorable: {fc.get('spray_window_favorable')} ({fc.get('spray_window_reason')})\n"
                    f"Forecast: {fc.get('summary')}\n"
                    f"Source: {curr.get('source')} (Observed: {curr.get('observed_at')})\n"
                )

        if self._advisory_tool is not None and crop:
            a_res = await self._advisory_tool.execute({"crop": crop, "district": district, "state": state})
            if a_res.success and "content" in a_res.data:
                advisory_data = a_res.data
                live_telemetry_str += (
                    f"\n[OFFICIAL AGROMET ADVISORY]\n"
                    f"Title: {advisory_data.get('title')}\n"
                    f"Advisory: {advisory_data.get('content')}\n"
                    f"Issuing Authority: {advisory_data.get('issuing_authority')}\n"
                )

        prompt = (
            f"User Query: {task}\n"
            f"Crop: {crop}, Region: {district or 'India'}, State: {state or 'India'}, Season: {context.season or 'General'}\n"
            f"{live_telemetry_str}\n"
            f"Verified ICAR/Dept Knowledge Base:\n{context_str}\n\n"
            "Generate actionable, grounded agricultural advice. Clearly distinguish live factual weather/market conditions from agronomic recommendations."
        )

        llm_resp = await self._llm.generate(
            prompt=prompt,
            system_instruction="You are an expert ICAR agronomist giving precise guidance to Indian farmers.",
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="synthesize_advisory",
            input_data={"task": task, "crop": crop},
            output_data={"tokens": llm_resp.total_tokens, "hits_used": len(hits)},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        confidence = float(hits[0].get("score", 0.7)) if hits else 0.5

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "recommendation": llm_resp.content,
                "crop": crop,
                "context_used": len(hits) > 0,
            },
            confidence_score=confidence,
            grounded=len(hits) > 0,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED and result.confidence_score >= 0.3

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name, "llm": self._llm.provider_name}
