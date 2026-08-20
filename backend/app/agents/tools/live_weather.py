"""Production Agent Tool for Live Weather & Forecast Intelligence."""

from time import perf_counter
from typing import Any

from app.agents.contracts.tool import BaseTool, RetryPolicy, ToolMetadata, ToolResult
from app.auth.permissions import Permission
from app.live_data.services.live_data_service import LiveDataService


class LiveWeatherTool(BaseTool):
    """Fetches real-time weather observations, forecasts, and agricultural spray advisories."""

    def __init__(self, service: LiveDataService | None = None) -> None:
        metadata = ToolMetadata(
            name="live_weather",
            description=(
                "Fetch verified real-time weather observations and multi-day agricultural forecasts "
                "for a farmer's field or district (temperature, rainfall probability, humidity, wind, and spray window)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Optional latitude coordinate"},
                    "longitude": {"type": "number", "description": "Optional longitude coordinate"},
                    "district": {"type": "string", "description": "District name (e.g. Warangal)"},
                    "state": {"type": "string", "description": "State name (e.g. Telangana)"},
                    "field_id": {"type": "integer", "description": "Field ID for exact farm plot lookup"},
                    "forecast_days": {"type": "integer", "default": 7, "description": "Forecast horizon (1-7 days)"},
                },
            },
            permissions=[Permission.WEATHER_READ, Permission.LIVE_DATA_READ],
            timeout_seconds=5.0,
            retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.5),
            supported_agent_types=["crop_advisory_agent", "weather_agent", "vision_intelligence_agent"],
        )
        super().__init__(metadata)
        self._service = service or LiveDataService()

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        t0 = perf_counter()
        lat = parameters.get("latitude")
        lon = parameters.get("longitude")
        dist = parameters.get("district")
        st = parameters.get("state")
        fid = parameters.get("field_id")
        days = int(parameters.get("forecast_days", 7))

        try:
            current_obs = await self._service.get_current_weather(
                latitude=lat,
                longitude=lon,
                district=dist,
                state=st,
                field_id=fid,
            )
            forecast = await self._service.get_weather_forecast(
                latitude=lat,
                longitude=lon,
                district=dist,
                state=st,
                field_id=fid,
                days=days,
            )

            data = {
                "location": {
                    "district": current_obs.district,
                    "state": current_obs.state,
                    "latitude": current_obs.latitude,
                    "longitude": current_obs.longitude,
                },
                "current": {
                    "temperature_celsius": current_obs.temperature_celsius,
                    "relative_humidity_percent": current_obs.relative_humidity_percent,
                    "rainfall_mm": current_obs.rainfall_mm,
                    "wind_speed_mps": current_obs.wind_speed_mps,
                    "condition": current_obs.weather_condition,
                    "observed_at": current_obs.observed_at.isoformat(),
                    "freshness": current_obs.freshness.value,
                    "source": current_obs.source,
                },
                "forecast": {
                    "summary": forecast.summary,
                    "spray_window_favorable": forecast.spray_window_favorable,
                    "spray_window_reason": forecast.spray_window_reason,
                    "days": [d.model_dump() for d in forecast.forecast_days[:days]],
                },
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
