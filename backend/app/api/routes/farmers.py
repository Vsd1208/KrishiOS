"""REST endpoints for farmer registration and profile management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    AuthContext,
    RequirePermission,
    get_current_auth_context,
    linked_farmer_id,
)
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.schemas.farmer import FarmerCreate, FarmerResponse, FarmerUpdate
from app.services.farmer import FarmerService

router = APIRouter(prefix="/farmers", tags=["Farmers"])


async def _require_staff_or_self(session: AsyncSession, auth: AuthContext, farmer_id: int,
                                 staff: str, self_permission: str) -> None:
    """Staff holding ``staff`` may act on any farmer; a farmer holding ``self_permission`` only
    on their own linked profile. Others get 404, so profiles can't be probed by id."""
    if auth.has_permission(staff):
        return
    if (auth.has_permission(self_permission)
            and await linked_farmer_id(session, auth) == farmer_id):
        return
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Farmer not found")


def get_farmer_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> FarmerService:
    """Build the farmer service for request-scoped database access."""
    return FarmerService(session)


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
async def register_farmer(
    payload: FarmerCreate,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FARMER_CREATE))],
) -> FarmerResponse:
    return await service.register_farmer(payload)


@router.get("", response_model=list[FarmerResponse])
async def list_farmers(
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FARMER_READ))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[FarmerResponse]:
    return list(await service.list_farmers(offset=offset, limit=limit))


@router.get("/me", response_model=FarmerResponse)
async def my_farmer_profile(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> FarmerResponse:
    """The farmer profile linked to the signed-in user (404 when none is linked)."""
    farmer_id = await linked_farmer_id(session, auth)
    if farmer_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No farmer profile is linked to this user")
    return await FarmerService(session).get_farmer(farmer_id)


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(
    farmer_id: int,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> FarmerResponse:
    await _require_staff_or_self(session, auth, farmer_id, Permission.FARMER_READ,
                                 Permission.FARMER_READ_SELF)
    return await service.get_farmer(farmer_id)


@router.patch("/{farmer_id}", response_model=FarmerResponse)
async def update_farmer(
    farmer_id: int,
    payload: FarmerUpdate,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> FarmerResponse:
    await _require_staff_or_self(session, auth, farmer_id, Permission.FARMER_UPDATE,
                                 Permission.FARMER_UPDATE_SELF)
    return await service.update_farmer(farmer_id, payload)


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farmer(
    farmer_id: int,
    service: Annotated[FarmerService, Depends(get_farmer_service)],
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.FARMER_DELETE))],
) -> Response:
    await service.delete_farmer(farmer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

