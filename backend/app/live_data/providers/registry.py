"""Registry for pluggable live data providers.

Sprint 11 (ADR-005): unknown provider names raise ``ProviderConfigurationError`` instead
of silently falling back to a mock, and every provider carries a ``ProviderInfo`` whose
``kind`` (live / sandbox / mock) is reported by ``GET /api/v1/providers``.
"""

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
from app.providers import ProviderInfo, ProviderKind, ProviderSelector

weather_selector: ProviderSelector[WeatherProvider] = ProviderSelector("weather")
market_selector: ProviderSelector[MarketDataProvider] = ProviderSelector("market")
advisory_selector: ProviderSelector[AdvisoryProvider] = ProviderSelector("advisory")
scheme_selector: ProviderSelector[GovernmentSchemeProvider] = ProviderSelector("scheme")


def _register_defaults() -> None:
    weather_selector.register(
        ProviderInfo("weather", "mock-weather-v1", "1.0.0", ProviderKind.MOCK,
                     description="Synthetic weather for tests and offline demos."),
        MockWeatherProvider,
    )
    weather_selector.register(
        ProviderInfo("weather", "open-meteo-v1", "1.0.0", ProviderKind.LIVE,
                     sends_data_off_device=False,
                     description="Open-Meteo forecast API (sends district coordinates only)."),
        lambda: OpenMeteoWeatherProvider(base_url=get_settings().WEATHER_API_BASE_URL),
    )
    market_selector.register(
        ProviderInfo("market", "mock-market-v1", "1.0.0", ProviderKind.MOCK,
                     description="Synthetic mandi prices."),
        MockMarketDataProvider,
    )
    market_selector.register(
        ProviderInfo("market", "agmarknet-v1", "1.0.0", ProviderKind.LIVE,
                     sends_data_off_device=False,
                     description="Official AGMARKNET daily mandi prices via data.gov.in "
                                 "(needs DATA_GOV_IN_API_KEY; sends state/district only)."),
        lambda: AgmarknetMarketProvider(
            api_base_url=get_settings().MARKET_API_BASE_URL,
            api_key=get_settings().DATA_GOV_IN_API_KEY,
            resource_id=get_settings().DATA_GOV_IN_AGMARKNET_RESOURCE),
    )
    advisory_selector.register(
        ProviderInfo("advisory", "mock-advisory-v1", "1.0.0", ProviderKind.MOCK,
                     description="Synthetic advisories."),
        MockAdvisoryProvider,
    )
    advisory_selector.register(
        ProviderInfo("advisory", "agromet-v1", "1.0.0", ProviderKind.MOCK,
                     description="Placeholder: mock subclass; officer upload / AAS pending."),
        AgrometAdvisoryProvider,
    )
    scheme_selector.register(
        ProviderInfo("scheme", "mock-scheme-v1", "1.0.0", ProviderKind.MOCK,
                     description="Synthetic scheme catalogue."),
        MockGovernmentSchemeProvider,
    )


_register_defaults()


class LiveDataProviderRegistry:
    """Resolves the configured live data providers (fail-loud on unknown names)."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def get_weather_provider(self, name: str | None = None) -> WeatherProvider:
        return weather_selector.get(name or self._settings.WEATHER_PROVIDER_NAME)

    def get_market_provider(self, name: str | None = None) -> MarketDataProvider:
        return market_selector.get(name or self._settings.MARKET_PROVIDER_NAME)

    def get_advisory_provider(self, name: str | None = None) -> AdvisoryProvider:
        return advisory_selector.get(name or self._settings.ADVISORY_PROVIDER_NAME)

    def get_scheme_provider(self, name: str | None = None) -> GovernmentSchemeProvider:
        return scheme_selector.get(name or self._settings.SCHEME_PROVIDER_NAME)
