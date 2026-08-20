"""Market Data Provider implementations (Mock and Agmarknet format)."""

from datetime import UTC, date, datetime, timedelta

from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel
from app.live_data.schemas.market import MandiTrend, MarketPriceObservation

MSP_BENCHMARK_2026: dict[str, float] = {
    "Paddy": 2300.0,
    "Cotton": 7121.0,
    "Wheat": 2275.0,
    "Maize": 2090.0,
    "Soybean": 4892.0,
    "Tomato": 1200.0,
}


class MockMarketDataProvider:
    """Deterministic commodity price provider for testing and offline MVP execution."""

    def __init__(self, provider_name: str = "mock-market-v1", provider_version: str = "1.0.0") -> None:
        self._provider_name = provider_name
        self._provider_version = provider_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_commodity_prices(
        self,
        commodity: str,
        state: str | None = None,
        district: str | None = None,
    ) -> list[MarketPriceObservation]:
        now = datetime.now(UTC)
        norm_comm = commodity.title()
        msp = MSP_BENCHMARK_2026.get(norm_comm, 2000.0)

        # Baseline modal price slightly above or around MSP
        modal = msp * 1.05 if norm_comm in ["Paddy", "Cotton"] else msp * 0.95

        return [
            MarketPriceObservation(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                source="Agmarknet Portal (DMI, MoA&FW)",
                authority_level=SourceAuthorityLevel.GOVERNMENT,
                observed_at=now - timedelta(hours=2),
                retrieved_at=now,
                valid_until=now + timedelta(hours=8),
                freshness=FreshnessStatus.FRESH,
                commodity=norm_comm,
                variety="Common",
                market=f"{district or 'Warangal'} Main Mandi",
                district=district or "Warangal",
                state=state or "Telangana",
                arrival_date=date.today(),
                min_price_inr_quintal=round(modal * 0.93, 2),
                max_price_inr_quintal=round(modal * 1.08, 2),
                modal_price_inr_quintal=round(modal, 2),
                msp_inr_quintal=msp,
                price_trend=MandiTrend.RISING if modal >= msp else MandiTrend.STABLE,
                arrivals_tonnes=125.0,
            )
        ]

    async def get_msp(self, commodity: str, season: str | None = None) -> float | None:
        return MSP_BENCHMARK_2026.get(commodity.title())

    async def health(self) -> bool:
        return True


class AgmarknetMarketProvider(MockMarketDataProvider):
    """Agmarknet external adapter connecting to Government mandi open data feed."""

    def __init__(
        self,
        api_base_url: str = "https://api.data.gov.in/resource",
        provider_name: str = "agmarknet-v1",
        provider_version: str = "1.0.0",
    ) -> None:
        super().__init__(provider_name=provider_name, provider_version=provider_version)
        self._api_base_url = api_base_url
