"""REST endpoints for district reference data."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.district import DistrictCreate, DistrictResponse, DistrictUpdate
from app.services.district import DistrictService

router = APIRouter(prefix="/districts", tags=["Districts"])


def get_district_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DistrictService:
    """Build the district service for request-scoped database access."""
    return DistrictService(session)


@router.post("", response_model=DistrictResponse, status_code=status.HTTP_201_CREATED)
async def create_district(
    payload: DistrictCreate,
    service: Annotated[DistrictService, Depends(get_district_service)],
) -> DistrictResponse:
    return await service.create_district(payload)


@router.get("", response_model=list[DistrictResponse])
async def list_districts(
    service: Annotated[DistrictService, Depends(get_district_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[DistrictResponse]:
    return list(await service.list_districts(offset=offset, limit=limit))


@router.get("/{district_id}", response_model=DistrictResponse)
async def get_district(
    district_id: int,
    service: Annotated[DistrictService, Depends(get_district_service)],
) -> DistrictResponse:
    return await service.get_district(district_id)


@router.patch("/{district_id}", response_model=DistrictResponse)
async def update_district(
    district_id: int,
    payload: DistrictUpdate,
    service: Annotated[DistrictService, Depends(get_district_service)],
) -> DistrictResponse:
    return await service.update_district(district_id, payload)


@router.delete("/{district_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_district(
    district_id: int,
    service: Annotated[DistrictService, Depends(get_district_service)],
) -> Response:
    await service.delete_district(district_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
