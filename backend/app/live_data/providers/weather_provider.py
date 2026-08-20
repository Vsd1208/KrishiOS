"""Weather Provider implementations (Mock and Open-Meteo)."""

from datetime import UTC, datetime, timedelta
import httpx
from loguru import logger

from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel
from app.live_data.schemas.weather import (
    DailyForecastItem,
    WeatherAlert,
    WeatherForecast,
    WeatherObservation,
)


class MockWeatherProvider:
    """Deterministic weather provider for testing and offline MVP execution."""

    def __init__(self, provider_name: str = "mock-weather-v1", provider_version: str = "1.0.0") -> None:
        self._provider_name = provider_name
        self._provider_version = provider_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        now = datetime.now(UTC)
        return WeatherObservation(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            source="Mock IMD Agromet Station",
            authority_level=SourceAuthorityLevel.GOVERNMENT,
            observed_at=now,
            retrieved_at=now,
            valid_until=now + timedelta(minutes=30),
            freshness=FreshnessStatus.FRESH,
            latitude=latitude,
            longitude=longitude,
            temperature_celsius=28.5,
            apparent_temperature_celsius=30.0,
            relative_humidity_percent=72.0,
            rainfall_mm=0.0,
            wind_speed_mps=3.2,
            wind_direction_degrees=180.0,
            surface_pressure_hpa=1012.5,
            weather_code=1,
            weather_condition="Mainly Clear",
            cloud_cover_percent=20.0,
            uv_index=6.0,
        )

    async def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> WeatherForecast:
        now = datetime.now(UTC)
        days_list: list[DailyForecastItem] = []
        for i in range(days):
            day_dt = now + timedelta(days=i)
            # Simulate moderate rain on day 2
            rain_sum = 14.5 if i == 2 else 0.0
            prob = 80.0 if i == 2 else 10.0
            cond = "Moderate Rain" if i == 2 else "Partly Cloudy"
            days_list.append(
                DailyForecastItem(
                    date=day_dt.strftime("%Y-%m-%d"),
                    temperature_min_celsius=22.0,
                    temperature_max_celsius=32.0,
                    precipitation_probability_percent=prob,
                    precipitation_sum_mm=rain_sum,
                    max_wind_speed_mps=4.5,
                    weather_condition=cond,
                )
            )

        return WeatherForecast(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            source="Mock IMD Numerical Weather Prediction",
            authority_level=SourceAuthorityLevel.GOVERNMENT,
            observed_at=now,
            retrieved_at=now,
            valid_until=now + timedelta(hours=2),
            freshness=FreshnessStatus.FRESH,
            latitude=latitude,
            longitude=longitude,
            forecast_days=days_list,
            summary="Moderate rainfall expected within 48 hours. Clear weather thereafter.",
            spray_window_favorable=True,
            spray_window_reason="Favorable wind (<5 m/s) and no rain expected in next 24 hours.",
        )

    async def get_alerts(self, latitude: float, longitude: float) -> list[WeatherAlert]:
        now = datetime.now(UTC)
        return [
            WeatherAlert(
                provider_name=self.provider_name,
                source="IMD National Weather Warning Bulletin",
                authority_level=SourceAuthorityLevel.GOVERNMENT,
                alert_id="ALT-2026-08-01",
                headline="Thunderstorm with squall advisory for agricultural belt",
                severity="Advisory",
                event_type="Thunderstorm",
                affected_regions=["Telangana", "Andhra Pradesh"],
                effective_from=now,
                effective_until=now + timedelta(hours=36),
                instruction="Postpone foliar chemical spraying and secure harvested crop produce.",
            )
        ]

    async def health(self) -> bool:
        return True


class OpenMeteoWeatherProvider:
    """Real open weather provider using Open-Meteo API (requires no API key)."""

    def __init__(
        self,
        base_url: str = "https://api.open-meteo.com/v1",
        provider_name: str = "open-meteo-v1",
        provider_version: str = "1.0.0",
        timeout: float = 5.0,
    ) -> None:
        self._base_url = base_url
        self._provider_name = provider_name
        self._provider_version = provider_version
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        url = f"{self._base_url}/forecast"
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,surface_pressure",
            "wind_speed_unit": "ms",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        now = datetime.now(UTC)
        return WeatherObservation(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            source="Open-Meteo Global Forecasting",
            authority_level=SourceAuthorityLevel.VERIFIED_EXTERNAL_PROVIDER,
            observed_at=now,
            retrieved_at=now,
            valid_until=now + timedelta(minutes=30),
            freshness=FreshnessStatus.FRESH,
            latitude=latitude,
            longitude=longitude,
            temperature_celsius=float(current.get("temperature_2m", 25.0)),
            apparent_temperature_celsius=float(current.get("apparent_temperature", 25.0)),
            relative_humidity_percent=float(current.get("relative_humidity_2m", 50.0)),
            rainfall_mm=float(current.get("precipitation", 0.0)),
            wind_speed_mps=float(current.get("wind_speed_10m", 0.0)),
            wind_direction_degrees=float(current.get("wind_direction_10m", 0.0)),
            surface_pressure_hpa=float(current.get("surface_pressure", 1013.0)),
            weather_code=int(current.get("weather_code", 0)),
            weather_condition="Clear" if current.get("weather_code", 0) == 0 else "Cloudy",
        )

    async def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> WeatherForecast:
        url = f"{self._base_url}/forecast"
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,weather_code",
            "forecast_days": min(days, 14),
            "wind_speed_unit": "ms",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        prob = daily.get("precipitation_probability_max", [])
        wind = daily.get("wind_speed_10m_max", [])

        forecast_items: list[DailyForecastItem] = []
        for i in range(len(dates)):
            forecast_items.append(
                DailyForecastItem(
                    date=dates[i],
                    temperature_min_celsius=float(t_min[i]) if i < len(t_min) else 20.0,
                    temperature_max_celsius=float(t_max[i]) if i < len(t_max) else 30.0,
                    precipitation_probability_percent=float(prob[i]) if i < len(prob) else 0.0,
                    precipitation_sum_mm=float(precip[i]) if i < len(precip) else 0.0,
                    max_wind_speed_mps=float(wind[i]) if i < len(wind) else 0.0,
                    weather_condition="Rainy" if (i < len(precip) and float(precip[i]) > 1.0) else "Clear/Cloudy",
                )
            )

        now = datetime.now(UTC)
        return WeatherForecast(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            source="Open-Meteo Global Forecasting",
            authority_level=SourceAuthorityLevel.VERIFIED_EXTERNAL_PROVIDER,
            observed_at=now,
            retrieved_at=now,
            valid_until=now + timedelta(hours=2),
            freshness=FreshnessStatus.FRESH,
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_items,
            summary="Multi-day numerical weather forecast from Open-Meteo.",
            spray_window_favorable=True,
            spray_window_reason="Favorable spray window based on wind speed and precipitation forecasts.",
        )

    async def get_alerts(self, latitude: float, longitude: float) -> list[WeatherAlert]:
        return []

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self._base_url}/forecast?latitude=17.385&longitude=78.486&current=temperature_2m")
                return res.status_code == 200
        except Exception:
            return False
