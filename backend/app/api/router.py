"""Top-level API router composition for KrishiOS."""

from fastapi import APIRouter

from app.api.routes import (
    crops,
    districts,
    documents,
    farmers,
    field_crops,
    fields,
    health,
    officers,
    soil_samples,
)
from app.retrieval.api.routes import router as retrieval_router
from app.agents.api.routes import router as agents_router

api_router = APIRouter()
# Sprint 0/1 — domain routes
api_router.include_router(health.router)
api_router.include_router(districts.router)
api_router.include_router(farmers.router)
api_router.include_router(officers.router)
api_router.include_router(fields.router)
api_router.include_router(crops.router)
api_router.include_router(field_crops.router)
api_router.include_router(soil_samples.router)
# Sprint 2 — knowledge infrastructure
api_router.include_router(documents.router)
api_router.include_router(retrieval_router)
api_router.include_router(agents_router)
