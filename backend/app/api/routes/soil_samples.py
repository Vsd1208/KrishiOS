"""REST endpoints for soil sample collection workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.soil_sample import SoilSampleCreate, SoilSampleResponse, SoilSampleUpdate
from app.services.soil_sample import SoilSampleService

router = APIRouter(prefix="/soil-samples", tags=["Soil Samples"])


def get_soil_sample_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SoilSampleService:
    """Build the soil sample service for request-scoped database access."""
    return SoilSampleService(session)


@router.post("", response_model=SoilSampleResponse, status_code=status.HTTP_201_CREATED)
async def register_soil_sample(
    payload: SoilSampleCreate,
    service: Annotated[SoilSampleService, Depends(get_soil_sample_service)],
) -> SoilSampleResponse:
    return await service.register_soil_sample(payload)


@router.get("", response_model=list[SoilSampleResponse])
async def list_soil_samples(
    service: Annotated[SoilSampleService, Depends(get_soil_sample_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SoilSampleResponse]:
    return list(await service.list_soil_samples(offset=offset, limit=limit))


@router.get("/{sample_id}", response_model=SoilSampleResponse)
async def get_soil_sample(
    sample_id: int,
    service: Annotated[SoilSampleService, Depends(get_soil_sample_service)],
) -> SoilSampleResponse:
    return await service.get_soil_sample(sample_id)


@router.patch("/{sample_id}", response_model=SoilSampleResponse)
async def update_soil_sample(
    sample_id: int,
    payload: SoilSampleUpdate,
    service: Annotated[SoilSampleService, Depends(get_soil_sample_service)],
) -> SoilSampleResponse:
    return await service.update_soil_sample(sample_id, payload)


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_soil_sample(
    sample_id: int,
    service: Annotated[SoilSampleService, Depends(get_soil_sample_service)],
) -> Response:
    await service.delete_soil_sample(sample_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

