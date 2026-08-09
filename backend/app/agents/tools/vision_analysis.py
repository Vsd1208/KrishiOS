"""Vision analysis tool for agents to read analysis results."""

from typing import Any
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.contracts.tool import BaseTool, ToolMetadata, ToolResult
from app.vision.models.analysis import ImageAnalysis, ImageAnalysisStatus


class VisionAnalysisTool(BaseTool):
    """Retrieves the completed structured findings of a vision model analysis."""

    def __init__(self, session_factory) -> None:
        metadata = ToolMetadata(
            name="vision_analysis",
            description="Retrieve the structured findings of a completed crop image analysis.",
            parameters={
                "type": "object",
                "properties": {
                    "analysis_id": {"type": "integer"},
                },
                "required": ["analysis_id"],
            },
            supported_agent_types=["vision_intelligence_agent", "crop_advisory_agent"],
        )
        super().__init__(metadata)
        self._session_factory = session_factory

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        analysis_id = parameters.get("analysis_id")

        if not analysis_id:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={},
                error_message="analysis_id is required",
            )

        async with self._session_factory() as session:
            stmt = select(ImageAnalysis).where(ImageAnalysis.id == analysis_id)
            result = await session.execute(stmt)
            analysis = result.scalar_one_or_none()

            if not analysis:
                return ToolResult(
                    tool_name=self.metadata.name,
                    success=False,
                    data={},
                    error_message=f"Analysis with ID {analysis_id} not found.",
                )

            if analysis.status != ImageAnalysisStatus.COMPLETED:
                return ToolResult(
                    tool_name=self.metadata.name,
                    success=False,
                    data={"status": analysis.status.value},
                    error_message=f"Analysis is not completed (current status: {analysis.status.value}).",
                )

            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data={
                    "analysis_id": analysis.id,
                    "crop_detected": analysis.findings.get("crop_detected"),
                    "observations": analysis.findings.get("observations", []),
                    "candidate_conditions": analysis.findings.get("candidate_conditions", []),
                    "confidence_score": analysis.confidence_score,
                },
                duration_ms=(perf_counter() - t0) * 1000,
            )
