"""REST endpoints for farmer registration and profile management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.farmer import FarmerCreate, FarmerResponse, FarmerUpdate
from app.services.farmer import FarmerService

router = APIRouter(prefix="/farmers", tags=["Farmers"])


def get_farmer_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> FarmerService:
    """Build the farmer service for request-scoped database access."""
    return FarmerService(session)


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def register_farmer(
    payload: FarmerCreate,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
) -> FarmerResponse:
    return await service.register_farmer(payload)


@router.get("", response_model=list[FarmerResponse])
async def list_farmers(
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FarmerResponse]:
    return list(await service.list_farmers(offset=offset, limit=limit))


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(
    farmer_id: int,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
) -> FarmerResponse:
    return await service.get_farmer(farmer_id)


@router.patch("/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(
    farmer_id: int,
    payload: FarmerUpdate,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
) -> FarmerResponse:
    return await service.update_farmer(farmer_id, payload)


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: int,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
) -> Response:
    await service.delete_farmer(farmer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

