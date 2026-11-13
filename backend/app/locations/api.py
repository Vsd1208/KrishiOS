"""Saved farmer locations (F2): several fields/villages, each with LGD district and block."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.catalog.lgd import get_lgd_directory
from app.database.session import get_db_session
from app.govconnect.api import current_farmer_id
from app.models.govconnect import FarmerLocation

router = APIRouter(prefix="/farmers/me/locations", tags=["Farmer locations (F2)"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Farmer = Annotated[AuthContext, Depends(RequirePermission(Permission.FARMER_UPDATE_SELF))]
MAX_LOCATIONS = 10


class LocationIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    lgd_district_code: int
    lgd_block_code: int | None = None
    village: str | None = Field(default=None, max_length=150)
    latitude: float | None = Field(default=None, ge=6, le=38)
    longitude: float | None = Field(default=None, ge=68, le=98)
    is_primary: bool = False


def validate_place(district_code: int, block_code: int | None) -> dict:
    lgd = get_lgd_directory()
    district = lgd.district(district_code)
    if district is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown LGD district code")
    block = None
    if block_code is not None:
        block = lgd.block(block_code)
        if block is None or block.lgd_district_code != district_code:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "The block does not belong to this district"
            )
    return {
        "district_name": district.district_name,
        "state_name": district.state_name,
        "block_name": block.block_name if block else None,
    }


def _out(loc: FarmerLocation) -> dict:
    return {
        "id": loc.id,
        "label": loc.label,
        "lgd_district_code": loc.lgd_district_code,
        "lgd_block_code": loc.lgd_block_code,
        "village": loc.village,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "is_primary": loc.is_primary,
        **validate_place(loc.lgd_district_code, loc.lgd_block_code),
    }


async def _clear_primary(session: AsyncSession, farmer_id: int) -> None:
    for loc in (
        await session.scalars(
            select(FarmerLocation).where(
                FarmerLocation.farmer_id == farmer_id, FarmerLocation.is_primary
            )
        )
    ).all():
        loc.is_primary = False


@router.get("")
async def list_locations(session: DbSession, auth: Farmer) -> list[dict]:
    farmer_id = await current_farmer_id(session, auth)
    rows = (
        await session.scalars(
            select(FarmerLocation)
            .where(FarmerLocation.farmer_id == farmer_id)
            .order_by(FarmerLocation.id)
        )
    ).all()
    return [_out(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_location(body: LocationIn, session: DbSession, auth: Farmer) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    validate_place(body.lgd_district_code, body.lgd_block_code)
    count = await session.scalar(
        select(func.count(FarmerLocation.id)).where(FarmerLocation.farmer_id == farmer_id)
    )
    if (count or 0) >= MAX_LOCATIONS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"At most {MAX_LOCATIONS} locations")
    if body.is_primary or not count:
        await _clear_primary(session, farmer_id)
    loc = FarmerLocation(
        farmer_id=farmer_id,
        **body.model_dump(exclude={"is_primary"}),
        is_primary=body.is_primary or not count,
    )
    session.add(loc)
    await session.commit()
    return _out(loc)


@router.put("/{location_id}")
async def update_location(
    location_id: int, body: LocationIn, session: DbSession, auth: Farmer
) -> dict:
    farmer_id = await current_farmer_id(session, auth)
    loc = await session.get(FarmerLocation, location_id)
    if loc is None or loc.farmer_id != farmer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    validate_place(body.lgd_district_code, body.lgd_block_code)
    if body.is_primary:
        await _clear_primary(session, farmer_id)
    for key, value in body.model_dump().items():
        setattr(loc, key, value)
    await session.commit()
    return _out(loc)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: int, session: DbSession, auth: Farmer) -> None:
    farmer_id = await current_farmer_id(session, auth)
    loc = await session.get(FarmerLocation, location_id)
    if loc is None or loc.farmer_id != farmer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    await session.delete(loc)
    await session.commit()
