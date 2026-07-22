"""REST endpoints for crop catalog management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.crop import CropCreate, CropResponse, CropUpdate
from app.services.crop import CropService

router = APIRouter(prefix="/crops", tags=["Crops"])


def get_crop_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> CropService:
    """Build the crop service for request-scoped database access."""
    return CropService(session)


@router.post("", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
async def create_crop(
    payload: CropCreate,
    service: Annotated[CropService, Depends(get_crop_service)],
) -> CropResponse:
    return await service.create_crop(payload)


@router.get("", response_model=list[CropResponse])
async def list_crops(
    service: Annotated[CropService, Depends(get_crop_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CropResponse]:
    return list(await service.list_crops(offset=offset, limit=limit))


@router.get("/{crop_id}", response_model=CropResponse)
async def get_crop(
    crop_id: int,
    service: Annotated[CropService, Depends(get_crop_service)],
) -> CropResponse:
    return await service.get_crop(crop_id)


@router.patch("/{crop_id}", response_model=CropResponse)
async def update_crop(
    crop_id: int,
    payload: CropUpdate,
    service: Annotated[CropService, Depends(get_crop_service)],
) -> CropResponse:
    return await service.update_crop(crop_id, payload)


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop(
    crop_id: int,
    service: Annotated[CropService, Depends(get_crop_service)],
) -> Response:
    await service.delete_crop(crop_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

