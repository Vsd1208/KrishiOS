"""Agent tool: identify the crop (and likely conditions) in a stored photo with the local
vision model. Low confidence or an unsupported crop is returned as ``needs_confirmation`` so
the agent asks the farmer instead of guessing. Images never leave the machine."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission


class CropIdentifyTool(BaseTool):
    def __init__(self, provider=None) -> None:
        super().__init__(ToolMetadata(
            name="crop_identify",
            description=("Identify the crop in a farmer's photo and list possible conditions "
                         "(local model; returns needs_confirmation when unsure)."),
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Stored image path"},
                    "confirmed_crop": {"type": "string",
                                       "description": "Crop key the farmer confirmed"},
                },
                "required": ["image_path"],
            },
            permissions=[Permission.VISION_ANALYZE],
            timeout_seconds=10.0,
            retry_policy=RetryPolicy(max_retries=0, backoff_seconds=0.0),
            supported_agent_types=["crop_advisory_agent", "officer_agent"],
        ))
        self._provider = provider

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        from app.conversation.manager import vision_to_dict  # noqa: PLC0415
        from app.vision.providers.selection import get_vision_provider  # noqa: PLC0415

        t0 = perf_counter()
        path = Path(str(parameters.get("image_path", "")))
        if not path.is_file():  # noqa: ASYNC240 - one cheap stat before CPU inference
            return ToolResult(tool_name=self.metadata.name, success=False, data={},
                              duration_ms=(perf_counter() - t0) * 1000,
                              error_message="image_path does not exist")
        provider = self._provider or get_vision_provider()
        r = await provider.analyze(path, {"confirmed_crop": parameters.get("confirmed_crop")})
        data = vision_to_dict(r)
        data["needs_confirmation"] = not r.crop_supported
        data["official"] = False
        return ToolResult(tool_name=self.metadata.name, success=True, data=data,
                          duration_ms=(perf_counter() - t0) * 1000)
