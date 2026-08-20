"""Top-level API router composition for KrishiOS."""

from fastapi import APIRouter

from app.api.routes import (
    auth,
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
# Sprint 5 — Identity
api_router.include_router(auth.router)
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

from app.graph.api.routes import router as graph_router
api_router.include_router(graph_router)

# Sprint 7 — Vision Intelligence
from app.vision.api.routes import router as vision_router
api_router.include_router(vision_router)

# Sprint 8 — Voice Intelligence
from app.voice.api.routes import router as voice_router
api_router.include_router(voice_router)

# Sprint 9 — Live Agricultural Intelligence
from app.live_data.api.routes import router as live_data_router
api_router.include_router(live_data_router)

