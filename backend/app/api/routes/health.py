from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.config.settings import Settings, get_settings
from app.health.service import HealthService

router = APIRouter(tags=["Health"])


def get_health_service(settings: Annotated[Settings, Depends(get_settings)]) -> HealthService:
    return HealthService(settings=settings)


@router.get("/")
async def root(service: Annotated[HealthService, Depends(get_health_service)]) -> dict[str, str]:
    return service.get_root()


@router.get("/health")
async def health(service: Annotated[HealthService, Depends(get_health_service)]) -> dict[str, str]:
    return service.get_health()


@router.get("/ready")
async def ready(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> dict[str, object]:
    readiness = await service.get_readiness()
    if readiness["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness


@router.get("/version")
async def version(service: Annotated[HealthService, Depends(get_health_service)]) -> dict[str, str]:
    return service.get_version()
