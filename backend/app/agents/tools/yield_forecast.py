"""Agent tool: the imported district yield forecast for a crop (Yield Intelligence).

Returns the forecast with its interval, normal yield, tier and review flags, or an abstention
with no number. Always marked ``official: False`` (a model estimate, not a crop-cutting,
YES-TECH or insurance figure).
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission


class YieldForecastTool(BaseTool):
    def __init__(self, lookup=None) -> None:
        super().__init__(ToolMetadata(
            name="yield_forecast",
            description=("District yield forecast for a crop and season (model estimate with "
                         "an uncertainty interval; abstains when data are insufficient)."),
            parameters={
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop name or alias"},
                    "lgd_district_code": {"type": "integer"},
                    "season": {"type": "string", "enum": ["Kharif", "Rabi", "Zaid",
                                                          "Whole Year"]},
                },
                "required": ["crop", "lgd_district_code"],
            },
            permissions=[Permission.ADVISORY_READ],
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.2),
            supported_agent_types=["crop_advisory_agent", "officer_agent"],
        ))
        self._lookup = lookup

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
        from app.conversation.manager import default_yield_lookup  # noqa: PLC0415

        t0 = perf_counter()

        def done(ok: bool, data: dict[str, Any], error: str | None = None) -> ToolResult:
            return ToolResult(tool_name=self.metadata.name, success=ok, data=data,
                              duration_ms=(perf_counter() - t0) * 1000, error_message=error)

        crop = get_crop_catalog().resolve_name(str(parameters.get("crop", "")))
        lgd = parameters.get("lgd_district_code")
        if crop is None or lgd is None:
            return done(False, {}, "crop (in the catalog) and lgd_district_code are required")
        try:
            f = await (self._lookup or default_yield_lookup)(int(lgd), crop,
                                                             parameters.get("season"))
        except Exception as exc:
            return done(False, {}, str(exc))
        if f is None:
            return done(True, {"crop": crop, "lgd_district_code": int(lgd),
                               "status": "no_forecast"})
        return done(True, {**f, "status": "abstained" if f["abstained"] else "ok",
                           "official": False})
