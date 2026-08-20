"""Normalized weather observation, forecast, and alert schemas."""

from datetime import datetime
from pydantic import BaseModel, Field

from app.live_data.schemas.common import BaseLiveDataResponse


class WeatherObservation(BaseLiveDataResponse):
    """Normalized weather observation at a specific geographic coordinate or district."""

    latitude: float
    longitude: float
    district: str | None = None
    state: str | None = None

    # Normalized scientific units
    temperature_celsius: float
    apparent_temperature_celsius: float | None = None
    relative_humidity_percent: float
    rainfall_mm: float = 0.0
    wind_speed_mps: float = 0.0
    wind_direction_degrees: float | None = None
    surface_pressure_hpa: float | None = None
    weather_code: int = 0
    weather_condition: str = "Clear"
    cloud_cover_percent: float | None = None
    uv_index: float | None = None


class DailyForecastItem(BaseModel):
    """Single day forecast entry."""

    date: str
    temperature_min_celsius: float
    temperature_max_celsius: float
    precipitation_probability_percent: float
    precipitation_sum_mm: float
    max_wind_speed_mps: float
    weather_condition: str


class WeatherForecast(BaseLiveDataResponse):
    """Multi-day agricultural weather forecast."""

    latitude: float
    longitude: float
    district: str | None = None
    state: str | None = None
    forecast_days: list[DailyForecastItem] = Field(default_factory=list)
    summary: str = ""
    spray_window_favorable: bool = True
    spray_window_reason: str = ""


class WeatherAlert(BaseLiveDataResponse):
    """Severe weather, cyclone, heatwave, or unseasonal rainfall warning."""

    alert_id: str
    headline: str
    severity: str  # "Advisory", "Watch", "Warning", "Emergency"
    event_type: str  # "Heatwave", "Heavy Rainfall", "Thunderstorm", "Frost"
    affected_regions: list[str] = Field(default_factory=list)
    effective_from: datetime
    effective_until: datetime
    instruction: str
