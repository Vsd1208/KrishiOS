"""REST endpoints for crops grown on fields (crop history).

Access follows the field: staff with ``field:*`` permissions see and manage all; a farmer reads
only the crops on their own fields. Deleting is for administrators.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission, farmer_scope
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.schemas.field_crop import FieldCropCreate, FieldCropResponse, FieldCropUpdate
from app.services.field import FieldService
from app.services.field_crop import FieldCropService

router = APIRouter(prefix="/field-crops", tags=["Field Crops"])
Db = Annotated[AsyncSession, Depends(get_db_session)]


def get_field_crop_service(session: Db) -> FieldCropService:
    """Build the field crop service for request-scoped database access."""
    return FieldCropService(session)


Service = Annotated[FieldCropService, Depends(get_field_crop_service)]


def _not_found(what: str) -> HTTPException:
    # Same answer as a missing record, so a farmer can't probe for other farmers' records.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.post("", response_model=FieldCropResponse, status_code=status.HTTP_201_CREATED)
async def assign_crop_to_field(
    payload: FieldCropCreate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_UPDATE))],
) -> FieldCropResponse:
    return await service.assign_crop(payload)


@router.get("", response_model=list[FieldCropResponse])
async def list_field_crops(
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_READ))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FieldCropResponse]:
    scope = await farmer_scope(session, auth)
    return list(await service.list_field_crops(offset=offset, limit=limit, farmer_id=scope))


@router.get("/{field_crop_id}", response_model=FieldCropResponse)
async def get_field_crop(
    field_crop_id: int,
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_READ))],
) -> FieldCropResponse:
    scope = await farmer_scope(session, auth)
    field_crop = await service.get_field_crop(field_crop_id)
    if scope is not None:
        field = await FieldService(session).get_field(field_crop.field_id)
        if field.farmer_id != scope:
            raise _not_found("Field crop")
    return field_crop


@router.patch("/{field_crop_id}", response_model=FieldCropResponse)
async def update_field_crop(
    field_crop_id: int,
    payload: FieldCropUpdate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_UPDATE))],
) -> FieldCropResponse:
    return await service.update_field_crop(field_crop_id, payload)


@router.delete("/{field_crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_crop(
    field_crop_id: int,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_DELETE))],
) -> Response:
    await service.delete_field_crop(field_crop_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
