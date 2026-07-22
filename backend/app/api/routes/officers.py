"""REST endpoints for officer registration and profile management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.officer import OfficerCreate, OfficerResponse, OfficerUpdate
from app.services.officer import OfficerService

router = APIRouter(prefix="/officers", tags=["Officers"])


def get_officer_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> OfficerService:
    """Build the officer service for request-scoped database access."""
    return OfficerService(session)


@router.post("", response_model=OfficerResponse, status_code=status.HTTP_201_CREATED)
async def register_officer(
    payload: OfficerCreate,
    service: Annotated[OfficerService, Depends(get_officer_service)],
) -> OfficerResponse:
    return await service.register_officer(payload)


@router.get("", response_model=list[OfficerResponse])
async def list_officers(
    service: Annotated[OfficerService, Depends(get_officer_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[OfficerResponse]:
    return list(await service.list_officers(offset=offset, limit=limit))


@router.get("/{officer_id}", response_model=OfficerResponse)
async def get_officer(
    officer_id: int,
    service: Annotated[OfficerService, Depends(get_officer_service)],
) -> OfficerResponse:
    return await service.get_officer(officer_id)


@router.patch("/{officer_id}", response_model=OfficerResponse)
async def update_officer(
    officer_id: int,
    payload: OfficerUpdate,
    service: Annotated[OfficerService, Depends(get_officer_service)],
) -> OfficerResponse:
    return await service.update_officer(officer_id, payload)


@router.delete("/{officer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_officer(
    officer_id: int,
    service: Annotated[OfficerService, Depends(get_officer_service)],
) -> Response:
    await service.delete_officer(officer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

