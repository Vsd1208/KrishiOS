"""Test-only yield provider: a fixed, clearly fake forecast (kind MOCK, never LIVE)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasting.schemas import YieldForecast


class MockYieldProvider:
    provider_name = "mock-yield"
    model_version = "mock-1"

    def _one(self, lgd: int, crop: str, season: str | None) -> YieldForecast:
        return YieldForecast(
            lgd_district_code=lgd, crop_canonical=crop, season=season or "Kharif",
            crop_year=2026, crop_tier="A", forecast_lead=30, unit="Tonnes/Hectare",
            model_name="mock", model_version=self.model_version,
            generated_at=datetime(2026, 1, 1, tzinfo=UTC), predicted_yield=3.0,
            interval_low=2.5, interval_high=3.5, normal_yield=3.2,
            available_modalities=["weather", "yield_history"],
        )

    async def forecast(
        self, session: AsyncSession, lgd_district_code: int, crop: str, season: str | None
    ) -> YieldForecast | None:
        return self._one(lgd_district_code, crop, season)

    async def outlook(
        self, session: AsyncSession, lgd_district_code: int, season: str | None
    ) -> list[YieldForecast]:
        return [self._one(lgd_district_code, "paddy", season)]
