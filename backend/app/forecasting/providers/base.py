"""Yield provider protocol. Providers never run a model inside the API: the batch provider
serves forecasts imported from the ml/ export, so serving matches what was validated."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasting.schemas import YieldForecast


class YieldProvider(Protocol):
    provider_name: str
    model_version: str

    async def forecast(
        self, session: AsyncSession, lgd_district_code: int, crop: str, season: str | None
    ) -> YieldForecast | None: ...

    async def outlook(
        self, session: AsyncSession, lgd_district_code: int, season: str | None
    ) -> list[YieldForecast]: ...
