"""Queries over imported forecasts: latest forecast, district outlook, likely shortfalls.

"Latest" = the newest import; within it, the latest crop year and the longest lead (the
forecast made with the most in-season information).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.forecasting.schemas import YieldForecast
from app.models.forecasting import ForecastImport, YieldForecastRecord


def to_forecast(r: YieldForecastRecord, district_id: int | None = None) -> YieldForecast:
    return YieldForecast(
        lgd_district_code=r.lgd_district_code, crop_canonical=r.crop_canonical, season=r.season,
        crop_year=r.crop_year, crop_tier=r.crop_tier, forecast_lead=r.forecast_lead,
        unit=r.unit, model_name=r.model_name, model_version=r.model_version,
        generated_at=r.generated_at, predicted_yield=r.predicted_yield,
        interval_low=r.interval_low, interval_high=r.interval_high,
        normal_yield=r.normal_yield, available_modalities=list(r.available_modalities or []),
        missing_modalities=list(r.missing_modalities or []), in_distribution=r.in_distribution,
        requires_human_review=r.requires_human_review, abstained=r.abstained,
        abstain_reason=r.abstain_reason, district_id=district_id,
    )


async def latest_import(session: AsyncSession) -> ForecastImport | None:
    return await session.scalar(select(ForecastImport).order_by(ForecastImport.id.desc()))


def _latest_per_crop(rows: list[YieldForecastRecord]) -> list[YieldForecastRecord]:
    best: dict[tuple[str, str], YieldForecastRecord] = {}
    for r in rows:
        k = (r.crop_canonical, r.season)
        cur = best.get(k)
        if cur is None or (r.crop_year, r.forecast_lead) > (cur.crop_year, cur.forecast_lead):
            best[k] = r
    return sorted(best.values(), key=lambda r: (r.abstained, r.crop_canonical, r.season))


async def outlook(
    session: AsyncSession, lgd_district_code: int, season: str | None = None
) -> list[YieldForecastRecord]:
    imp = await latest_import(session)
    if imp is None:
        return []
    q = select(YieldForecastRecord).where(YieldForecastRecord.import_id == imp.id,
                                          YieldForecastRecord.lgd_district_code
                                          == lgd_district_code)
    if season:
        q = q.where(YieldForecastRecord.season == season)
    return _latest_per_crop(list((await session.scalars(q)).all()))


async def forecast_for(
    session: AsyncSession, lgd_district_code: int, crop: str, season: str | None = None
) -> YieldForecastRecord | None:
    rows = [r for r in await outlook(session, lgd_district_code, season)
            if r.crop_canonical == crop]
    return rows[0] if rows else None


def is_shortfall(r: YieldForecastRecord, pct: float | None = None) -> bool:
    """Likely shortfall: the forecast is at least ``pct`` below normal **and** even the upper
    end of the interval is below normal (the model is confident about the direction)."""
    pct = get_settings().YIELD_SHORTFALL_PCT if pct is None else pct
    if r.abstained or r.predicted_yield is None or not r.normal_yield or r.interval_high is None:
        return False
    return (r.predicted_yield <= (1 - pct) * r.normal_yield
            and r.interval_high < r.normal_yield)


async def shortfalls(session: AsyncSession, import_id: int) -> list[YieldForecastRecord]:
    rows = (await session.scalars(select(YieldForecastRecord).where(
        YieldForecastRecord.import_id == import_id))).all()
    latest = _latest_per_crop_by_district(list(rows))
    return [r for r in latest if is_shortfall(r)]


def _latest_per_crop_by_district(rows: list[YieldForecastRecord]) -> list[YieldForecastRecord]:
    by_d: dict[int, list[YieldForecastRecord]] = {}
    for r in rows:
        by_d.setdefault(r.lgd_district_code, []).append(r)
    return [r for d in sorted(by_d) for r in _latest_per_crop(by_d[d])]
