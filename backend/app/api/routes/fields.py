"""REST endpoints for farmer field management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.field import FieldCreate, FieldResponse, FieldUpdate
from app.services.field import FieldService

router = APIRouter(prefix="/fields", tags=["Fields"])


def get_field_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> FieldService:
    """Build the field service for request-scoped database access."""
    return FieldService(session)


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def register_field(
    payload: FieldCreate,
    service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    return await service.register_field(payload)


@router.get("", response_model=list[FieldResponse])
async def list_fields(
    service: Annotated[FieldService, Depends(get_field_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FieldResponse]:
    return list(await service.list_fields(offset=offset, limit=limit))


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: int,
    service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    return await service.get_field(field_id)


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: int,
    payload: FieldUpdate,
    service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    return await service.update_field(field_id, payload)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: int,
    service: Annotated[FieldService, Depends(get_field_service)],
) -> Response:
    await service.delete_field(field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

