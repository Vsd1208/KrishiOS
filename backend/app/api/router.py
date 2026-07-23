"""Top-level API router composition for KrishiOS."""

from fastapi import APIRouter

from app.api.routes import (
    crops,
    districts,
    farmers,
    field_crops,
    fields,
    health,
    officers,
    soil_samples,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(districts.router)
api_router.include_router(farmers.router)
api_router.include_router(officers.router)
api_router.include_router(fields.router)
api_router.include_router(crops.router)
api_router.include_router(field_crops.router)
api_router.include_router(soil_samples.router)
