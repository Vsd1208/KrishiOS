"""Serves imported batch forecasts (B3 multi-crop LightGBM in Phase 8)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasting import service
from app.forecasting.schemas import YieldForecast


class BatchForecastProvider:
    provider_name = "baseline-lgbm-batch"
    model_version = "imported"

    async def forecast(
        self, session: AsyncSession, lgd_district_code: int, crop: str, season: str | None
    ) -> YieldForecast | None:
        r = await service.forecast_for(session, lgd_district_code, crop, season)
        return service.to_forecast(r) if r else None

    async def outlook(
        self, session: AsyncSession, lgd_district_code: int, season: str | None
    ) -> list[YieldForecast]:
        return [service.to_forecast(r) for r in
                await service.outlook(session, lgd_district_code, season)]
