"""REST endpoints for soil sample tracking.

Access: staff with ``soil_sample:*`` permissions see and manage all samples; a farmer reads only
their own. There is no delete permission for samples, so deleting is for administrators.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission, farmer_scope
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.schemas.soil_sample import SoilSampleCreate, SoilSampleResponse, SoilSampleUpdate
from app.services.soil_sample import SoilSampleService

router = APIRouter(prefix="/soil-samples", tags=["Soil Samples"])
Db = Annotated[AsyncSession, Depends(get_db_session)]


def get_soil_sample_service(session: Db) -> SoilSampleService:
    """Build the soil sample service for request-scoped database access."""
    return SoilSampleService(session)


Service = Annotated[SoilSampleService, Depends(get_soil_sample_service)]


def _not_found(what: str) -> HTTPException:
    # Same answer as a missing record, so a farmer can't probe for other farmers' records.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.post("", response_model=SoilSampleResponse, status_code=status.HTTP_201_CREATED)
async def register_soil_sample(
    payload: SoilSampleCreate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.SOIL_SAMPLE_CREATE))],
) -> SoilSampleResponse:
    return await service.register_soil_sample(payload)


@router.get("", response_model=list[SoilSampleResponse])
async def list_soil_samples(
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.SOIL_SAMPLE_READ))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SoilSampleResponse]:
    scope = await farmer_scope(session, auth)
    return list(await service.list_soil_samples(offset=offset, limit=limit, farmer_id=scope))


@router.get("/{sample_id}", response_model=SoilSampleResponse)
async def get_soil_sample(
    sample_id: int,
    service: Service,
    session: Db,
    auth: Annotated[AuthContext, Depends(RequirePermission(Permission.SOIL_SAMPLE_READ))],
) -> SoilSampleResponse:
    scope = await farmer_scope(session, auth)
    sample = await service.get_soil_sample(sample_id)
    if scope is not None and sample.farmer_id != scope:
        raise _not_found("Soil sample")
    return sample


@router.patch("/{sample_id}", response_model=SoilSampleResponse)
async def update_soil_sample(
    sample_id: int,
    payload: SoilSampleUpdate,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.SOIL_SAMPLE_UPDATE))],
) -> SoilSampleResponse:
    return await service.update_soil_sample(sample_id, payload)


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_soil_sample(
    sample_id: int,
    service: Service,
    _: Annotated[AuthContext, Depends(RequirePermission(Permission.SYSTEM_ADMIN))],
) -> Response:
    await service.delete_soil_sample(sample_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
