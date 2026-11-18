"""F8 officer API: district x week heat grid of crowd photo diagnoses and possible outbreaks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RequirePermission
from app.auth.permissions import Permission
from app.catalog.lgd import get_lgd_directory
from app.catalog.resolver import get_crop_catalog
from app.database.session import get_db_session
from app.surveillance.service import find_outbreaks, heat_grid, week_start

router = APIRouter(prefix="/surveillance", tags=["Outbreak surveillance (F8)"],
                   dependencies=[Depends(RequirePermission(Permission.ADVISORY_CREATE))])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _names(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lgd, catalog = get_lgd_directory(), get_crop_catalog()
    for c in cells:
        d, e = lgd.district(c["lgd_district_code"]), catalog.get(c["crop"])
        c["district_name"] = d.district_name if d else None
        c["state_name"] = d.state_name if d else None
        c["crop_name"] = e.name_en if e else c["crop"]
    return cells


@router.get("/heatmap")
async def heatmap(session: DbSession, weeks: int = Query(8, ge=1, le=26),
                  crop: str | None = None) -> dict[str, Any]:
    cells = _names(await heat_grid(session, weeks=weeks, crop=crop))
    return {"weeks": weeks, "cells": cells,
            "note": "Distinct farmers per week whose photos the local model read as this "
                    "condition. Unverified model findings, not diagnoses."}


@router.get("/outbreaks")
async def outbreaks(session: DbSession) -> dict[str, Any]:
    today = datetime.now(UTC).date()
    found = find_outbreaks(await heat_grid(session, weeks=5, today=today), week_start(today))
    items = _names([{"lgd_district_code": o.lgd_district_code, "crop": o.crop,
                     "condition": o.condition, "week_start": o.week_start.isoformat(),
                     "reporters": o.reporters, "baseline": o.baseline} for o in found])
    return {"week_start": week_start(today).isoformat(), "items": items}
