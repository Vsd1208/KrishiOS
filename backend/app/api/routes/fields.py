"""REST endpoints for farmer field management.

Access: staff with ``field:*`` permissions see and manage all fields; a farmer reads only the
fields of their own linked profile. Deleting is for administrators.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission, farmer_scope
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.schemas.field import FieldCreate, FieldResponse, FieldUpdate
from app.services.field import FieldService

router = APIRouter(prefix="/fields", tags=["Fields"])
Db = Annotated[AsyncSession, Depends(get_db_session)]


def get_field_service(session: Db) -> FieldService:
    """Build the field service for request-scoped database access."""
    return FieldService(session)


Service = Annotated[FieldService, Depends(get_field_service)]


def _not_found(what: str) -> HTTPException:
    # Same answer as a missing record, so a farmer can't probe for other farmers' records.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def register_field(
    payload: FieldCreate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_CREATE))],
) -> FieldResponse:
    return await service.register_field(payload)


@router.get("", response_model=list[FieldResponse])
async def list_fields(
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_READ))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FieldResponse]:
    scope = await farmer_scope(session, auth)
    return list(await service.list_fields(offset=offset, limit=limit, farmer_id=scope))


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: int,
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_READ))],
) -> FieldResponse:
    scope = await farmer_scope(session, auth)
    field = await service.get_field(field_id)
    if scope is not None and field.farmer_id != scope:
        raise _not_found("Field")
    return field


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: int,
    payload: FieldUpdate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_UPDATE))],
) -> FieldResponse:
    return await service.update_field(field_id, payload)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: int,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FIELD_DELETE))],
) -> Response:
    await service.delete_field(field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
