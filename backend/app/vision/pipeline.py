"""Vision analysis pipeline orchestrator."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.vision.models.image import CropImage
from app.vision.models.analysis import ImageAnalysis, ImageAnalysisStatus, ReviewStatus
from app.vision.services.quality import QualityAssessor
from app.vision.services.preprocessor import ImagePreprocessor
from app.vision.providers.base import VisionModelProvider
from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.types import ExtractedEntity


class VisionAnalysisPipeline:
    """Orchestrates the image quality checks, preprocessing, and model inference."""

    def __init__(
        self,
        session: AsyncSession,
        provider: VisionModelProvider,
        quality_assessor: QualityAssessor,
        preprocessor: ImagePreprocessor,
        entity_resolver: EntityResolver,
    ) -> None:
        self._session = session
        self._provider = provider
        self._quality_assessor = quality_assessor
        self._preprocessor = preprocessor
        self._entity_resolver = entity_resolver

    async def run(self, analysis_id: int) -> None:
        """Run the full analysis pipeline for a given analysis record."""
        # 1. Fetch record
        stmt = select(ImageAnalysis).where(ImageAnalysis.id == analysis_id)
        result = await self._session.execute(stmt)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            logger.error("VisionPipeline: Analysis {} not found", analysis_id)
            return

        stmt = select(CropImage).where(CropImage.id == analysis.image_id)
        result = await self._session.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            await self._set_status(analysis, ImageAnalysisStatus.FAILED, "Image record not found")
            return

        analysis.started_at = datetime.now(UTC)
        await self._set_status(analysis, ImageAnalysisStatus.VALIDATING)

        try:
            image_path = Path(image.storage_key)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found at {image_path}")

            # 2. Quality Assessment
            quality_report = self._quality_assessor.assess(image_path)
            analysis.quality_score = quality_report.score
            analysis.quality_issues = quality_report.issues

            if not quality_report.usable:
                await self._set_status(
                    analysis, 
                    ImageAnalysisStatus.FAILED, 
                    f"Image quality insufficient: {', '.join(quality_report.issues)}"
                )
                return

            await self._set_status(analysis, ImageAnalysisStatus.PROCESSING)

            # 3. Preprocessing (runs synchronously in this MVP, should be threadpool in prod)
            preprocessed_path = await asyncio.to_thread(self._preprocessor.preprocess, image_path)

            # 4. Model Inference
            metadata = {"crop_hint": image.crop_hint}
            vision_result = await self._provider.analyze(preprocessed_path, metadata)
            
            # 5. Entity Resolution (convert vision terms to graph entities)
            # E.g., "yellowing leaves" -> resolved entity in graph
            # This allows the VisionAgent to query GraphRAG
            
            resolved_observations = []
            for obs in vision_result.observations:
                ext_entity = ExtractedEntity(
                    raw_text=obs.finding, 
                    entity_type="symptom", 
                    confidence=obs.confidence,
                )
                res_entity = self._entity_resolver.resolve(ext_entity)
                
                # Store original + resolved (if any)
                resolved_observations.append({
                    "finding": obs.finding,
                    "confidence": obs.confidence,
                    "bbox": obs.bbox,
                    "resolved_entity": res_entity.canonical_name if res_entity else None
                })
                
            resolved_candidates = []
            max_conf = 0.0
            for cond in vision_result.candidate_conditions:
                max_conf = max(max_conf, cond.confidence)
                ext_entity = ExtractedEntity(
                    raw_text=cond.name, 
                    entity_type="disease", # simplistic mapping
                    confidence=cond.confidence,
                )
                res_entity = self._entity_resolver.resolve(ext_entity)
                resolved_candidates.append({
                    "name": cond.name,
                    "confidence": cond.confidence,
                    "resolved_entity": res_entity.canonical_name if res_entity else None
                })

            # 6. Save results
            findings = {
                "crop_detected": vision_result.crop_detected,
                "observations": resolved_observations,
                "candidate_conditions": resolved_candidates,
                "inference_ms": vision_result.inference_ms,
            }
            
            analysis.findings = findings
            analysis.confidence_score = max_conf
            
            # Decide review status
            from app.config.settings import get_settings
            settings = get_settings()
            
            if max_conf < settings.VISION_CONFIDENCE_THRESHOLD:
                analysis.review_status = ReviewStatus.AI_SUGGESTED
                
            analysis.completed_at = datetime.now(UTC)
            await self._set_status(analysis, ImageAnalysisStatus.COMPLETED)
            
        except Exception as e:
            logger.exception("VisionPipeline: Unhandled error analyzing image {}", analysis_id)
            await self._set_status(analysis, ImageAnalysisStatus.FAILED, str(e))

    async def _set_status(self, analysis: ImageAnalysis, status: ImageAnalysisStatus, error: str | None = None) -> None:
        """Update status and commit transaction."""
        analysis.status = status
        if error:
            analysis.error_message = error
        await self._session.commit()
        await self._session.refresh(analysis)
        logger.info("VisionPipeline: Analysis {} status -> {}", analysis.id, status.value)
