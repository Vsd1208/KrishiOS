"""Context Collection Engine for Proactive Decision Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.events.contracts import EventEnvelope
from app.models.crop import Crop
from app.models.district import District
from app.models.farmer import Farmer
from app.models.field import Field
from app.models.field_crop import FieldCrop, FieldCropStatus


@dataclass(slots=True)
class FarmerFieldContext:
    """Targeted contextual information for a farmer and their cultivated field."""

    farmer_id: int
    farmer_name: str
    phone: str
    preferred_language: str
    district_id: int
    district_name: str
    state_name: str
    village: str
    landholding_acres: float

    field_id: int | None = None
    field_name: str | None = None
    soil_type: str | None = None
    irrigation_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    crop_id: int | None = None
    crop_name: str | None = None
    crop_stage: str | None = None
    sowing_date: str | None = None

    live_weather: dict[str, Any] = field(default_factory=dict)
    live_advisory: dict[str, Any] = field(default_factory=dict)
    live_market: dict[str, Any] = field(default_factory=dict)
    recent_vision_findings: list[dict[str, Any]] = field(default_factory=list)
    graph_knowledge_paths: list[str] = field(default_factory=list)
    vector_rag_snippets: list[str] = field(default_factory=list)

    def to_evaluation_context(self) -> dict[str, Any]:
        """Convert to flat dictionary for rule evaluation."""
        return {
            "farmer_id": self.farmer_id,
            "farmer_name": self.farmer_name,
            "preferred_language": self.preferred_language,
            "district": self.district_name,
            "state": self.state_name,
            "village": self.village,
            "landholding_acres": self.landholding_acres,
            "field_id": self.field_id,
            "field_name": self.field_name,
            "soil_type": self.soil_type,
            "irrigation_type": self.irrigation_type,
            "crop": self.crop_name,
            "crop_stage": self.crop_stage,
            "sowing_date": self.sowing_date,
            "live_weather": self.live_weather,
            "live_advisory": self.live_advisory,
            "live_market": self.live_market,
            "recent_vision_findings": self.recent_vision_findings,
            "graph_paths": self.graph_knowledge_paths,
            "rag_snippets": self.vector_rag_snippets,
        }


class ProactiveContextEngine:
    """Asynchronously gathers multi-source context across domain models, live data, and RAG."""

    def __init__(
        self,
        session: AsyncSession,
        live_data_service: Any | None = None,
        graph_retriever: Any | None = None,
        vector_pipeline: Any | None = None,
    ) -> None:
        self._session = session
        self._live_data = live_data_service
        self._graph_retriever = graph_retriever
        self._vector_pipeline = vector_pipeline

    async def collect_contexts_for_event(
        self, event: EventEnvelope, max_targets: int = 100
    ) -> list[FarmerFieldContext]:
        """Identify affected farmers and fields, then enrich each with multi-source agricultural context."""
        payload = event.payload or {}
        target_farmer_id = payload.get("farmer_id")
        target_field_id = payload.get("field_id")
        target_district_name = str(payload.get("district", "")).strip()
        target_state_name = str(payload.get("state", "")).strip()

        # Build query for farmers and fields
        stmt = (
            select(Farmer)
            .options(
                selectinload(Farmer.district),
                selectinload(Farmer.fields).selectinload(Field.crop_history).selectinload(FieldCrop.crop),
            )
            .where(Farmer.is_deleted == False)
        )

        if target_farmer_id:
            stmt = stmt.where(Farmer.id == int(target_farmer_id))
        elif target_district_name:
            stmt = stmt.join(District, Farmer.district_id == District.id).where(
                District.name.ilike(f"%{target_district_name}%")
            )
            if target_state_name:
                stmt = stmt.where(District.state.ilike(f"%{target_state_name}%"))

        stmt = stmt.limit(max_targets)
        result = await self._session.execute(stmt)
        farmers = result.scalars().all()

        contexts: list[FarmerFieldContext] = []
        for farmer in farmers:
            district_name = farmer.district.name if farmer.district else (target_district_name or "Unknown")
            state_name = farmer.district.state if farmer.district else (target_state_name or "Unknown")

            # If farmer has no registered fields, still produce a base farmer context
            if not farmer.fields:
                ctx = FarmerFieldContext(
                    farmer_id=farmer.id,
                    farmer_name=farmer.full_name,
                    phone=farmer.phone,
                    preferred_language=farmer.preferred_language,
                    district_id=farmer.district_id,
                    district_name=district_name,
                    state_name=state_name,
                    village=farmer.village,
                    landholding_acres=float(farmer.landholding_acres),
                )
                contexts.append(ctx)
                continue

            for field_obj in farmer.fields:
                if field_obj.is_deleted:
                    continue
                if target_field_id and field_obj.id != int(target_field_id):
                    continue

                # Find active standing crop
                active_crop = next(
                    (
                        fc
                        for fc in field_obj.crop_history
                        if not fc.is_deleted and fc.status in [FieldCropStatus.GROWING, FieldCropStatus.SOWN, FieldCropStatus.PLANNED]
                    ),
                    None,
                )

                crop_name = active_crop.crop.name if active_crop and active_crop.crop else None
                crop_stage = active_crop.status.value if active_crop else None
                sowing_date = str(active_crop.sowing_date) if active_crop else None

                ctx = FarmerFieldContext(
                    farmer_id=farmer.id,
                    farmer_name=farmer.full_name,
                    phone=farmer.phone,
                    preferred_language=farmer.preferred_language,
                    district_id=farmer.district_id,
                    district_name=district_name,
                    state_name=state_name,
                    village=farmer.village,
                    landholding_acres=float(farmer.landholding_acres),
                    field_id=field_obj.id,
                    field_name=field_obj.field_name,
                    soil_type=field_obj.soil_type,
                    irrigation_type=field_obj.irrigation_type,
                    latitude=float(field_obj.latitude),
                    longitude=float(field_obj.longitude),
                    crop_id=active_crop.crop_id if active_crop else None,
                    crop_name=crop_name,
                    crop_stage=crop_stage,
                    sowing_date=sowing_date,
                )
                contexts.append(ctx)

        # Enrich contexts with live data & RAG knowledge
        for ctx in contexts:
            await self._enrich_context(ctx, event)

        return contexts

    async def _enrich_context(self, ctx: FarmerFieldContext, event: EventEnvelope) -> None:
        """Enrich a context instance with live telemetry, graph paths, and RAG knowledge."""
        # 1. Live Weather & Advisories
        if self._live_data is not None:
            try:
                if ctx.district_name:
                    weather = await self._live_data.get_weather(ctx.district_name, ctx.state_name)
                    if weather:
                        ctx.live_weather = weather.dict() if hasattr(weather, "dict") else dict(weather)
                    
                    if ctx.crop_name:
                        advisory = await self._live_data.get_advisory(ctx.crop_name, ctx.district_name, ctx.state_name)
                        if advisory:
                            ctx.live_advisory = advisory.dict() if hasattr(advisory, "dict") else dict(advisory)
            except Exception as exc:
                logger.debug("ContextEngine: live data enrichment skipped: {}", exc)

        # 2. Graph Knowledge Paths
        if self._graph_retriever is not None and ctx.crop_name:
            try:
                query = f"{ctx.crop_name} disease pest management"
                graph_res = await self._graph_retriever.retrieve(query=query)
                if graph_res and hasattr(graph_res, "paths"):
                    ctx.graph_knowledge_paths = [p.path_text for p in graph_res.paths[:3]]
            except Exception as exc:
                logger.debug("ContextEngine: graph retrieval skipped: {}", exc)

        # 3. Vector RAG Snippets
        if self._vector_pipeline is not None and ctx.crop_name:
            try:
                from app.retrieval.interfaces.types import RetrievalFilters
                query = f"{ctx.crop_name} weather advisory risk management"
                filters = RetrievalFilters(crop=ctx.crop_name)
                rag_res = await self._vector_pipeline.search(query=query, filters=filters, top_k=2)
                if rag_res and hasattr(rag_res, "results"):
                    ctx.vector_rag_snippets = [r.answer_context for r in rag_res.results[:2]]
            except Exception as exc:
                logger.debug("ContextEngine: vector RAG retrieval skipped: {}", exc)
