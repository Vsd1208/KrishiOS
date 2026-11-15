"""Config-driven yield provider selection (``YIELD_PROVIDER``)."""

from __future__ import annotations

from app.config.settings import get_settings
from app.forecasting.providers.base import YieldProvider
from app.forecasting.providers.batch import BatchForecastProvider
from app.forecasting.providers.mock import MockYieldProvider
from app.providers import ProviderInfo, ProviderKind, ProviderSelector
from app.providers.status import register_capability

yield_selector: ProviderSelector[YieldProvider] = ProviderSelector("yield")

yield_selector.register(
    ProviderInfo("yield", "baseline-lgbm-batch", "imported", ProviderKind.LIVE,
                 description="Imported batch forecasts from the validated multi-crop LightGBM "
                             "(B3); tier C abstains."),
    BatchForecastProvider,
)
yield_selector.register(
    ProviderInfo("yield", "mock-yield", MockYieldProvider.model_version, ProviderKind.MOCK,
                 description="Fixed fake forecast for tests."),
    MockYieldProvider,
)

register_capability("yield", lambda s: s.YIELD_PROVIDER, lambda: yield_selector)


def get_yield_provider() -> YieldProvider:
    return yield_selector.get(get_settings().YIELD_PROVIDER)
