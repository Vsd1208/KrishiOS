"""Weather Provider implementations (Mock and Open-Meteo)."""

from datetime import UTC, datetime, timedelta

import httpx

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


SPRAY_MAX_WIND_MPS = 4.0  # about 15 km/h
SPRAY_MAX_RAIN_PROBABILITY = 40.0


def spray_window(day: DailyForecastItem | None) -> tuple[bool, str]:
    """Rule of thumb from the forecast: avoid spraying in strong wind or when rain is likely."""
    if day is None:
        return False, "No forecast available; spray window unknown."
    if day.max_wind_speed_mps > SPRAY_MAX_WIND_MPS:
        return False, (f"Wind up to {day.max_wind_speed_mps * 3.6:.0f} km/h today "
                       "(above about 15 km/h): spray may drift.")
    if day.precipitation_probability_percent >= SPRAY_MAX_RAIN_PROBABILITY:
        return False, (f"{day.precipitation_probability_percent:.0f}% chance of rain today: "
                       "spray may wash off.")
    return True, (f"Wind up to {day.max_wind_speed_mps * 3.6:.0f} km/h and "
                  f"{day.precipitation_probability_percent:.0f}% chance of rain today.")


def _num(series: list | None, i: int) -> float | None:
    if not series or i >= len(series) or series[i] is None:
        return None
    return float(series[i])


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
        for required in ("temperature_2m", "relative_humidity_2m"):
            if current.get(required) is None:  # never substitute a made-up value
                raise ValueError(f"Open-Meteo response is missing {required}")
        now = datetime.now(UTC)

        def opt(key: str) -> float | None:
            value = current.get(key)
            return float(value) if value is not None else None

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
            temperature_celsius=float(current["temperature_2m"]),
            apparent_temperature_celsius=opt("apparent_temperature"),
            relative_humidity_percent=float(current["relative_humidity_2m"]),
            rainfall_mm=opt("precipitation") or 0.0,
            wind_speed_mps=opt("wind_speed_10m") or 0.0,
            wind_direction_degrees=opt("wind_direction_10m"),
            surface_pressure_hpa=opt("surface_pressure"),
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

        def at(series: list, i: int) -> float | None:
            return float(series[i]) if i < len(series) and series[i] is not None else None

        forecast_items: list[DailyForecastItem] = []
        dropped = 0
        for i in range(len(dates)):
            values = [at(t_min, i), at(t_max, i), at(prob, i), at(precip, i), at(wind, i)]
            if any(v is None for v in values):  # a day with missing values is dropped, not filled
                dropped += 1
                continue
            lo, hi, p_rain, rain, w = values
            forecast_items.append(
                DailyForecastItem(
                    date=dates[i], temperature_min_celsius=lo, temperature_max_celsius=hi,
                    precipitation_probability_percent=p_rain, precipitation_sum_mm=rain,
                    max_wind_speed_mps=w,
                    weather_condition="Rainy" if rain > 1.0 else "Clear/Cloudy",
                )
            )
        favorable, reason = spray_window(forecast_items[0] if forecast_items else None)

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
            summary=("Multi-day numerical weather forecast from Open-Meteo."
                     + (f" {dropped} day(s) without complete data were left out." if dropped
                        else "")),
            spray_window_favorable=favorable,
            spray_window_reason=reason,
        )

    async def get_daily_history(self, latitude: float, longitude: float,
                                past_days: int = 7) -> dict[str, dict[str, float | None]]:
        """Model values for the last ``past_days`` days (for the cross-check)."""
        params = {"latitude": round(latitude, 4), "longitude": round(longitude, 4),
                  "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                  "past_days": past_days, "forecast_days": 1, "timezone": "Asia/Kolkata"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base_url}/forecast", params=params)
            resp.raise_for_status()
            daily = resp.json().get("daily", {})
        out: dict[str, dict[str, float | None]] = {}
        for i, day in enumerate(daily.get("time", [])):
            out[day] = {"precip_mm": _num(daily.get("precipitation_sum"), i),
                        "tmax_c": _num(daily.get("temperature_2m_max"), i),
                        "tmin_c": _num(daily.get("temperature_2m_min"), i)}
        return out

    async def get_alerts(self, latitude: float, longitude: float) -> list[WeatherAlert]:
        return []

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self._base_url}/forecast?latitude=17.385&longitude=78.486&current=temperature_2m")
                return res.status_code == 200
        except Exception:
            return False
