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

# Sprint 10 — Proactive Decision Intelligence
from app.proactive.api.routes import router as proactive_router
api_router.include_router(proactive_router)


# Sprint 11 — Platform foundations: crop catalog, provider transparency, job health
from app.catalog.api.routes import router as catalog_router
from app.providers.api.routes import router as providers_router
from app.worker.api import router as worker_health_router
api_router.include_router(catalog_router)
api_router.include_router(providers_router)
api_router.include_router(worker_health_router)

# Sprint 11 — Multilingual core: translation, NLU
from app.translation.api.routes import router as translation_router
api_router.include_router(translation_router)
from app.nlu.api.routes import router as nlu_router
api_router.include_router(nlu_router)

# Sprint 11 — Phase 3: multilingual bot, assisted mode (F6), media (F7), feedback (F13)
from app.conversation.api import router as conversation_router
from app.extension.api import router as extension_router
from app.feedback.api import router as feedback_router
from app.media.api import router as media_router
api_router.include_router(conversation_router)
api_router.include_router(extension_router)
api_router.include_router(feedback_router)
api_router.include_router(media_router)

# ── Sprint 11, Phase 4: Govt Connect, locations (F2), grievances and schemes (F4) ──
from app.govconnect.api import router as govconnect_router  # noqa: E402
from app.grievance.api import router as grievance_router  # noqa: E402
from app.locations.api import router as locations_router  # noqa: E402
from app.schemes.api import router as schemes_router  # noqa: E402

api_router.include_router(govconnect_router)
api_router.include_router(grievance_router)
api_router.include_router(locations_router)
api_router.include_router(schemes_router)
