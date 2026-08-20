"""Protocols defining pluggable external data provider interfaces."""

from typing import Protocol, runtime_checkable

from app.live_data.schemas.advisory import AgriculturalAdvisory
from app.live_data.schemas.market import MarketPriceObservation
from app.live_data.schemas.scheme import GovernmentScheme
from app.live_data.schemas.weather import (
    WeatherAlert,
    WeatherForecast,
    WeatherObservation,
)


@runtime_checkable
class WeatherProvider(Protocol):
    """Protocol for pluggable weather telemetry backends."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def provider_version(self) -> str:
        ...

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherObservation:
        """Fetch real-time weather observation for coordinates."""
        ...

    async def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> WeatherForecast:
        """Fetch multi-day agricultural weather forecast."""
        ...

    async def get_alerts(self, latitude: float, longitude: float) -> list[WeatherAlert]:
        """Fetch active meteorological warnings / heatwave / frost alerts."""
        ...

    async def health(self) -> bool:
        """Check provider operational status."""
        ...


@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol for pluggable agricultural commodity market backends (Agmarknet/e-NAM)."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def provider_version(self) -> str:
        ...

    async def get_commodity_prices(
        self,
        commodity: str,
        state: str | None = None,
        district: str | None = None,
    ) -> list[MarketPriceObservation]:
        """Fetch latest mandi price arrivals for commodity in district/state."""
        ...

    async def get_msp(self, commodity: str, season: str | None = None) -> float | None:
        """Fetch Minimum Support Price (MSP) in INR/quintal for crop."""
        ...

    async def health(self) -> bool:
        ...


@runtime_checkable
class AdvisoryProvider(Protocol):
    """Protocol for pluggable agricultural advisory backends (ICAR/State Agromet)."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def provider_version(self) -> str:
        ...

    async def get_advisories(
        self,
        crop: str,
        state: str,
        district: str | None = None,
    ) -> list[AgriculturalAdvisory]:
        """Fetch active official agricultural and agromet advisories."""
        ...

    async def health(self) -> bool:
        ...


@runtime_checkable
class GovernmentSchemeProvider(Protocol):
    """Protocol for pluggable central and state welfare scheme databases."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def provider_version(self) -> str:
        ...

    async def get_schemes(
        self,
        state: str | None = None,
        crop: str | None = None,
        farmer_category: str | None = None,
    ) -> list[GovernmentScheme]:
        """Query official welfare and subsidy schemes matching farmer context."""
        ...

    async def get_scheme_by_id(self, scheme_id: str) -> GovernmentScheme | None:
        """Fetch specific scheme details."""
        ...

    async def health(self) -> bool:
        ...
