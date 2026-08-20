"""Registry for pluggable live data providers."""

from loguru import logger

from app.config.settings import get_settings
from app.live_data.providers.advisory_provider import (
    AgrometAdvisoryProvider,
    MockAdvisoryProvider,
)
from app.live_data.providers.base import (
    AdvisoryProvider,
    GovernmentSchemeProvider,
    MarketDataProvider,
    WeatherProvider,
)
from app.live_data.providers.market_provider import (
    AgmarknetMarketProvider,
    MockMarketDataProvider,
)
from app.live_data.providers.scheme_provider import (
    MockGovernmentSchemeProvider,
)
from app.live_data.providers.weather_provider import (
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
)


class LiveDataProviderRegistry:
    """Central registry resolving and caching active live data providers."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._weather_providers: dict[str, WeatherProvider] = {}
        self._market_providers: dict[str, MarketDataProvider] = {}
        self._advisory_providers: dict[str, AdvisoryProvider] = {}
        self._scheme_providers: dict[str, GovernmentSchemeProvider] = {}

        self._register_defaults()

    def _register_defaults(self) -> None:
        # Weather
        self._weather_providers["mock-weather-v1"] = MockWeatherProvider()
        self._weather_providers["open-meteo-v1"] = OpenMeteoWeatherProvider(
            base_url=self._settings.WEATHER_API_BASE_URL
        )

        # Market
        self._market_providers["mock-market-v1"] = MockMarketDataProvider()
        self._market_providers["agmarknet-v1"] = AgmarknetMarketProvider(
            api_base_url=self._settings.MARKET_API_BASE_URL
        )

        # Advisory
        self._advisory_providers["mock-advisory-v1"] = MockAdvisoryProvider()
        self._advisory_providers["agromet-v1"] = AgrometAdvisoryProvider()

        # Schemes
        self._scheme_providers["mock-scheme-v1"] = MockGovernmentSchemeProvider()

    def get_weather_provider(self, name: str | None = None) -> WeatherProvider:
        prov_name = name or self._settings.WEATHER_PROVIDER_NAME
        if prov_name not in self._weather_providers:
            logger.warning("Weather provider '{}' not found, falling back to mock", prov_name)
            prov_name = "mock-weather-v1"
        return self._weather_providers[prov_name]

    def get_market_provider(self, name: str | None = None) -> MarketDataProvider:
        prov_name = name or self._settings.MARKET_PROVIDER_NAME
        if prov_name not in self._market_providers:
            logger.warning("Market provider '{}' not found, falling back to mock", prov_name)
            prov_name = "mock-market-v1"
        return self._market_providers[prov_name]

    def get_advisory_provider(self, name: str | None = None) -> AdvisoryProvider:
        prov_name = name or self._settings.ADVISORY_PROVIDER_NAME
        if prov_name not in self._advisory_providers:
            logger.warning("Advisory provider '{}' not found, falling back to mock", prov_name)
            prov_name = "mock-advisory-v1"
        return self._advisory_providers[prov_name]

    def get_scheme_provider(self, name: str | None = None) -> GovernmentSchemeProvider:
        prov_name = name or self._settings.SCHEME_PROVIDER_NAME
        if prov_name not in self._scheme_providers:
            logger.warning("Scheme provider '{}' not found, falling back to mock", prov_name)
            prov_name = "mock-scheme-v1"
        return self._scheme_providers[prov_name]
