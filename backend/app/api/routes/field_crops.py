"""REST endpoints for assigning crops to fields and querying crop history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.field_crop import FieldCropCreate, FieldCropResponse, FieldCropUpdate
from app.services.field_crop import FieldCropService

router = APIRouter(prefix="/field-crops", tags=["Field Crops"])


def get_field_crop_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FieldCropService:
    """Build the field crop service for request-scoped database access."""
    return FieldCropService(session)


@router.post("", response_model=FieldCropResponse, status_code=status.HTTP_201_CREATED)
async def assign_crop_to_field(
    payload: FieldCropCreate,
    service: Annotated[FieldCropService, Depends(get_field_crop_service)],
) -> FieldCropResponse:
    return await service.assign_crop(payload)


@router.get("", response_model=list[FieldCropResponse])
async def list_field_crops(
    service: Annotated[FieldCropService, Depends(get_field_crop_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FieldCropResponse]:
    return list(await service.list_field_crops(offset=offset, limit=limit))


@router.get("/{field_crop_id}", response_model=FieldCropResponse)
async def get_field_crop(
    field_crop_id: int,
    service: Annotated[FieldCropService, Depends(get_field_crop_service)],
) -> FieldCropResponse:
    return await service.get_field_crop(field_crop_id)


@router.patch("/{field_crop_id}", response_model=FieldCropResponse)
async def update_field_crop(
    field_crop_id: int,
    payload: FieldCropUpdate,
    service: Annotated[FieldCropService, Depends(get_field_crop_service)],
) -> FieldCropResponse:
    return await service.update_field_crop(field_crop_id, payload)


@router.delete("/{field_crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_crop(
    field_crop_id: int,
    service: Annotated[FieldCropService, Depends(get_field_crop_service)],
) -> Response:
    await service.delete_field_crop(field_crop_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

