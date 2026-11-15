"""Yield Intelligence API: model info, per-crop forecast (farmers), district outlook (officers)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RequirePermission
from app.auth.permissions import Permission
from app.catalog.lgd import get_lgd_directory
from app.catalog.resolver import get_crop_catalog
from app.config.settings import get_settings
from app.database.session import get_db_session
from app.forecasting import service
from app.forecasting.schemas import SEASONS, YieldForecast
from app.forecasting.selection import get_yield_provider, yield_selector

router = APIRouter(prefix="/forecasting", tags=["Yield Intelligence"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _card(f: YieldForecast) -> dict[str, Any]:
    entry = get_crop_catalog().get(f.crop_canonical)
    d = f.to_dict()
    d["crop_names"] = ({"en": entry.name_en, "hi": entry.name_hi, "te": entry.name_te}
                       if entry else {"en": f.crop_canonical})
    d["likely_shortfall"] = (not f.abstained and f.normal_yield is not None
                             and f.interval_high is not None
                             and f.change_vs_normal is not None
                             and f.change_vs_normal <= -get_settings().YIELD_SHORTFALL_PCT
                             and f.interval_high < f.normal_yield)
    d["official"] = False  # model estimate; never an official or insurance figure
    return d


def _district(lgd_district_code: int) -> dict[str, Any]:
    ref = get_lgd_directory().district(lgd_district_code)
    if ref is None:
        raise HTTPException(404, f"unknown LGD district code {lgd_district_code}")
    return {"lgd_district_code": lgd_district_code, "district_name": ref.district_name,
            "state_name": ref.state_name}


@router.get("/model", dependencies=[Depends(RequirePermission(Permission.ADVISORY_READ))])
async def model_info(session: DbSession) -> dict[str, Any]:

    name = get_settings().YIELD_PROVIDER
    imp = await service.latest_import(session)
    return {
        "provider": name, "provider_kind": yield_selector.info(name).kind.value,
        "latest_import": None if imp is None else {
            "model_name": imp.model_name, "model_version": imp.model_version,
            "rows": imp.rows, "imported_at": imp.imported_at.isoformat(),
            "generated_at": imp.manifest.get("generated_at"),
            "target": imp.manifest.get("target"),
            "validation": imp.manifest.get("validation"),
        },
    }


@router.get("/forecast", dependencies=[Depends(RequirePermission(Permission.ADVISORY_READ))])
async def forecast(
    session: DbSession,
    lgd_district_code: int = Query(...),
    crop: str = Query(..., description="Crop name in any catalog language or alias"),
    season: str | None = Query(None),
) -> dict[str, Any]:
    if season and season not in SEASONS:
        raise HTTPException(422, f"season must be one of {SEASONS}")
    crop_key = get_crop_catalog().resolve_name(crop)
    if crop_key is None:
        raise HTTPException(404, f"crop {crop!r} is not in the crop catalog")
    f = await get_yield_provider().forecast(session, lgd_district_code, crop_key, season)
    return {"district": _district(lgd_district_code), "crop": crop_key,
            "forecast": _card(f) if f else None,
            "status": "ok" if f else "no_forecast"}


@router.get("/outlook", dependencies=[Depends(RequirePermission(Permission.ADVISORY_CREATE))])
async def outlook(
    session: DbSession,
    lgd_district_code: int = Query(...),
    season: str | None = Query(None),
) -> dict[str, Any]:
    if season and season not in SEASONS:
        raise HTTPException(422, f"season must be one of {SEASONS}")
    rows = await get_yield_provider().outlook(session, lgd_district_code, season)
    cards = [_card(f) for f in rows]
    return {"district": _district(lgd_district_code), "season": season, "items": cards,
            "counts": {"forecasts": sum(not c["abstained"] for c in cards),
                       "abstained": sum(c["abstained"] for c in cards),
                       "likely_shortfall": sum(c["likely_shortfall"] for c in cards),
                       "needs_review": sum(c["requires_human_review"] for c in cards)}}


@router.post("/import", dependencies=[Depends(RequirePermission(Permission.ADVISORY_CREATE))])
async def run_import() -> dict[str, Any]:
    from app.worker.jobs.base import JobSkipped  # noqa: PLC0415
    from app.worker.jobs.forecasting import forecast_import  # noqa: PLC0415

    try:
        return await forecast_import({})
    except JobSkipped as exc:
        return {"imported": False, "reason": str(exc)}
