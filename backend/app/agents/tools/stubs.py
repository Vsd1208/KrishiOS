"""Tool stubs and interfaces for Weather, Market, Govt DB, Calculator, and Media tools."""

from time import perf_counter
from typing import Any

from app.agents.tools.base import BaseTool, ToolMetadata, ToolResult


class WeatherApiTool(BaseTool):
    """Stub tool interface for Weather Intelligence."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="weather_api",
            description="Fetch real-time weather forecasts, rainfall data, and agricultural climate advisories.",
            parameters={
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "district": {"type": "string"},
                },
                "required": ["state", "district"],
            },
            supported_agent_types=["weather_agent", "crop_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        district = parameters.get("district", "Unknown")
        data = {
            "district": district,
            "temperature_celsius": 29.5,
            "humidity_percent": 75,
            "forecast": "Moderate rainfall expected over next 48 hours.",
            "advisory": "Ensure drainage channels in field are clear.",
        }
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data=data,
            duration_ms=(perf_counter() - t0) * 1000,
        )


class MarketApiTool(BaseTool):
    """Stub tool interface for Mandi & Market Prices."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="market_api",
            description="Fetch mandi prices, MSP trends, and market demand for agricultural commodities.",
            parameters={
                "type": "object",
                "properties": {
                    "crop": {"type": "string"},
                    "state": {"type": "string"},
                },
                "required": ["crop"],
            },
            supported_agent_types=["crop_agent", "officer_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        crop = parameters.get("crop", "Crop")
        data = {
            "crop": crop,
            "modal_price_per_quintal": 2183.0,
            "msp": 2183.0,
            "trend": "Stable",
        }
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data=data,
            duration_ms=(perf_counter() - t0) * 1000,
        )


class GovernmentDbTool(BaseTool):
    """Stub tool interface for Government Welfare Scheme Lookup."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="government_db",
            description="Query PM-KISAN, PMFBY insurance, and state subsidy database records.",
            parameters={
                "type": "object",
                "properties": {
                    "scheme_name": {"type": "string"},
                    "state": {"type": "string"},
                },
                "required": ["scheme_name"],
            },
            supported_agent_types=["govt_agent", "officer_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        scheme = parameters.get("scheme_name", "")
        data = {
            "scheme": scheme,
            "status": "Active",
            "subsidy_percentage": 50.0,
            "eligibility": "Small and marginal farmers holding < 2 hectares",
        }
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data=data,
            duration_ms=(perf_counter() - t0) * 1000,
        )


class CalculatorTool(BaseTool):
    """Utility tool for seed rate, fertilizer dosage, and yield calculations."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="calculator",
            description="Perform precise mathematical calculations for seed rate and NPK fertilizer requirements.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression e.g. '120 * 2.5'"},
                },
                "required": ["expression"],
            },
            supported_agent_types=["crop_agent", "officer_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        expr = str(parameters.get("expression", "0"))
        try:
            # Safe restricted eval for basic math
            allowed = set("0123456789+-*/. ()")
            if not set(expr).issubset(allowed):
                raise ValueError("Disallowed characters in math expression")
            val = eval(expr, {"__builtins__": None}, {})  # noqa: S307
            return ToolResult(
                tool_name=self.metadata.name,
                success=True,
                data={"result": float(val)},
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


class VisionModelTool(BaseTool):
    """Interface tool for crop disease and pest image analysis."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="vision_model",
            description="Analyze crop images for disease, pest, and nutrient deficiency detection.",
            parameters={
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                    "crop": {"type": "string"},
                },
                "required": ["image_url"],
            },
            supported_agent_types=["crop_advisory_agent", "knowledge_retrieval_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data={
                "image_url": parameters.get("image_url"),
                "analysis": "Image analysis interface ready for future vision model integration.",
                "detected_issues": [],
                "confidence": 0.0,
            },
            duration_ms=(perf_counter() - t0) * 1000,
        )


class SpeechModelTool(BaseTool):
    """Interface tool for speech-to-text and text-to-speech conversion."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="speech_model",
            description="Convert farmer voice queries to text and responses to spoken audio.",
            parameters={
                "type": "object",
                "properties": {
                    "audio_url": {"type": "string"},
                    "language": {"type": "string", "default": "hi"},
                },
                "required": ["audio_url"],
            },
            supported_agent_types=["officer_assistance_agent", "crop_advisory_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data={
                "audio_url": parameters.get("audio_url"),
                "transcript": "Speech model interface ready for future integration.",
                "language": parameters.get("language", "hi"),
            },
            duration_ms=(perf_counter() - t0) * 1000,
        )


class NotificationServiceTool(BaseTool):
    """Interface tool for SMS, push, and IVR notifications to farmers."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            name="notification_service",
            description="Send agricultural advisories via SMS, push notification, or IVR to farmers.",
            parameters={
                "type": "object",
                "properties": {
                    "recipient_id": {"type": "string"},
                    "message": {"type": "string"},
                    "channel": {"type": "string", "enum": ["sms", "push", "ivr"]},
                },
                "required": ["recipient_id", "message"],
            },
            supported_agent_types=["officer_assistance_agent"],
        )
        super().__init__(metadata)

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        return ToolResult(
            tool_name=self.metadata.name,
            success=True,
            data={
                "recipient_id": parameters.get("recipient_id"),
                "channel": parameters.get("channel", "sms"),
                "status": "queued",
                "message_preview": str(parameters.get("message", ""))[:100],
            },
            duration_ms=(perf_counter() - t0) * 1000,
        )
