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
