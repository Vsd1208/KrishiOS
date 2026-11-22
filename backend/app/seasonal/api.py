"""Phase 10d: ``GET /seasonal/outlook`` (officers; research outlook alongside IMD)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.auth import RequirePermission
from app.auth.permissions import Permission
from app.seasonal.service import OutlookUnavailableError, get_outlook, season_view

router = APIRouter(prefix="/seasonal", tags=["Seasonal outlook"])


@router.get("/outlook", dependencies=[Depends(RequirePermission(Permission.ADVISORY_CREATE))])
async def outlook(
    season: Annotated[Literal["JJAS", "OND", "JF", "MAM"], Query()] = "JJAS",
    state: Annotated[str | None, Query(max_length=100)] = None,
    district_code: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, Any]:
    """Chance of below / near / above normal rainfall and temperature per district for a season.

    Officers only (same permission as the yield outlook): it is a research outlook alongside
    IMD's official forecasts, and anything for farmers goes through officer approval. Variables
    without tested skill come back with ``display = "withhold"`` and no probabilities.
    """
    try:
        body = get_outlook()
    except OutlookUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return season_view(body, season, state, district_code)
