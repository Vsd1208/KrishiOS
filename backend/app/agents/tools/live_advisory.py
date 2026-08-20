"""Production Agent Tool for Live Agromet Advisories."""

from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission
from app.live_data.services.live_data_service import LiveDataService


class LiveAdvisoryTool(BaseTool):
    """Fetches active ICAR/Agromet regional crop advisories."""

    def __init__(self, service: LiveDataService | None = None) -> None:
        metadata = ToolMetadata(
            name="live_advisory",
            description=(
                "Fetch verified ICAR and State Agricultural Department agromet advisories, "
                "active warnings, and recommended cultural practices for specific crops."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop name (e.g. Paddy, Cotton)"},
                    "state": {"type": "string", "description": "State name (e.g. Telangana)"},
                    "district": {"type": "string", "description": "District name (e.g. Warangal)"},
                },
                "required": ["crop"],
            },
            permissions=[Permission.ADVISORY_READ, Permission.LIVE_DATA_READ],
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.5),
            supported_agent_types=["crop_advisory_agent", "crop_agent", "officer_agent"],
        )
        super().__init__(metadata)
        self._service = service or LiveDataService()

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        crop = parameters.get("crop", "")
        st = parameters.get("state")
        dist = parameters.get("district")

        if not crop:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={},
                duration_ms=(perf_counter() - t0) * 1000,
                error_message="Crop parameter is required.",
            )

        try:
            advisories = await self._service.get_advisories(
                crop=crop,
                state=st,
                district=dist,
            )

            if not advisories:
                return ToolResult(
                    tool_name=self.metadata.name,
                    success=True,
                    data={"crop": crop, "advisories": [], "message": f"No active advisories for {crop}."},
                    duration_ms=(perf_counter() - t0) * 1000,
                )

            adv = advisories[0]
            data = {
                "advisory_id": adv.advisory_id,
                "title": adv.title,
                "content": adv.content,
                "crop": adv.crop,
                "issuing_authority": adv.issuing_authority,
                "effective_from": adv.effective_from.isoformat(),
                "effective_until": adv.effective_until.isoformat(),
                "status": adv.status.value,
                "recommended_practices": adv.recommended_practices,
                "warning_notes": adv.warning_notes,
                "source": adv.source,
                "freshness": adv.freshness.value,
            }

            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data=data,
                duration_ms=(perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.metadata.name,
                success=False,
                data={},
                duration_ms=(perf_counter() - t0) * 1000,
                error_message=str(exc),
            )
