"""Vision Intelligence Agent."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.contracts.agent import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.providers.llm import LLMProvider
from app.agents.tools.knowledge_search import KnowledgeSearchTool
from app.agents.tools.vision_analysis import VisionAnalysisTool


class VisionIntelligenceAgent(BaseAgent):
    """Integrates vision findings with enterprise knowledge to produce evidence-backed advisories."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        search_tool: KnowledgeSearchTool,
        vision_tool: VisionAnalysisTool,
    ) -> None:
        metadata = AgentMetadata(
            name="vision_intelligence_agent",
            description="Analyzes crop images and provides evidence-backed advisories.",
            capabilities=["vision_analysis", "crop_health", "pest_control"],
            input_schema={"analysis_id": "integer"},
            output_schema={"recommendation": "string", "citations": "list"},
            supported_tools=["vision_analysis", "knowledge_search"],
            priority=25,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._llm = llm_provider
        self._search_tool = search_tool
        self._vision_tool = vision_tool

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("VisionIntelligenceAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING
        params = parameters or {}
        analysis_id = params.get("analysis_id")

        if not analysis_id:
            self._status = AgentStatus.FAILED
            return self._build_error_result(context, "analysis_id is required", t0)

        # 1. Get Vision Findings
        vision_res = await self._vision_tool.execute({"analysis_id": analysis_id})
        if not vision_res.success:
            self._status = AgentStatus.FAILED
            return self._build_error_result(context, vision_res.error_message or "Failed to get vision findings", t0)

        vision_data = vision_res.data
        crop = vision_data.get("crop_detected", "Unknown")
        confidence = vision_data.get("confidence_score", 0.0)
        observations = vision_data.get("observations", [])
        candidates = vision_data.get("candidate_conditions", [])

        # 2. Build search query from findings
        search_terms = []
        for obs in observations:
            if obs.get("resolved_entity"):
                search_terms.append(obs["resolved_entity"])
            else:
                search_terms.append(obs.get("finding", ""))
                
        for cand in candidates:
            if cand.get("resolved_entity"):
                search_terms.append(cand["resolved_entity"])
            else:
                search_terms.append(cand.get("name", ""))

        search_query = f"{crop} {' '.join(search_terms)}"

        # 3. Retrieve Evidence
        search_res = await self._search_tool.execute({
            "query": search_query,
            "crop": crop if crop != "Unknown" else None,
            "top_k": 3,
        })
        
        hits = search_res.data.get("hits", [])
        context_str = "\n---\n".join([h.get("chunk_text", "") for h in hits])
        citations = [h.get("citation") for h in hits if h.get("citation")]

        # 4. Synthesize with LLM
        prompt = (
            f"Task: {task}\n"
            f"Vision Model Findings for Crop: {crop}\n"
            f"Observations: {observations}\n"
            f"Candidate Conditions: {candidates}\n"
            f"Vision Confidence: {confidence}\n\n"
            f"Verified ICAR/Dept Knowledge:\n{context_str}\n\n"
            "Generate actionable, grounded agricultural advice based on the vision findings and verified knowledge. "
            "If the vision confidence is low (< 0.5) or candidates are uncertain, state the uncertainty clearly and recommend consulting an expert."
        )

        llm_resp = await self._llm.generate(
            prompt=prompt,
            system_instruction="You are an expert ICAR agronomist giving precise guidance to Indian farmers based on visual evidence and verified knowledge.",
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="synthesize_vision_advisory",
            input_data={"analysis_id": analysis_id, "crop": crop, "query": search_query},
            output_data={"tokens": llm_resp.total_tokens, "hits_used": len(hits)},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "recommendation": llm_resp.content,
                "crop": crop,
                "context_used": len(hits) > 0,
                "vision_confidence": confidence,
            },
            confidence_score=confidence,
            grounded=len(hits) > 0,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    def _build_error_result(self, context: ExecutionContext, message: str, t0: float) -> ExecutionResult:
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.FAILED,
            agent_name=self.metadata.name,
            output={},
            confidence_score=0.0,
            grounded=False,
            error_message=message,
            duration_ms=(perf_counter() - t0) * 1000,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name}
