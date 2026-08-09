"""Tests for the VisionAnalysisPipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from uuid import uuid4

from app.vision.pipeline import VisionAnalysisPipeline
from app.vision.models.analysis import ImageAnalysis, ImageAnalysisStatus
from app.vision.models.image import CropImage


@pytest.mark.asyncio
async def test_pipeline_failed_quality(monkeypatch):
    # Mock session
    session = AsyncMock()
    
    # Mock models
    analysis = ImageAnalysis(id=1, image_id=1, status=ImageAnalysisStatus.UPLOADED)
    image = CropImage(id=1, storage_key="dummy.jpg", crop_hint="paddy")
    
    # Setup mock query results
    async def mock_execute(stmt):
        mock_result = MagicMock()
        if "ImageAnalysis" in str(stmt):
            mock_result.scalar_one_or_none.return_value = analysis
        elif "CropImage" in str(stmt):
            mock_result.scalar_one_or_none.return_value = image
        return mock_result
        
    session.execute = mock_execute
    
    # Mock quality assessor returning unusable
    quality_assessor = MagicMock()
    quality_report = MagicMock()
    quality_report.usable = False
    quality_report.score = 0.2
    quality_report.issues = ["Too dark"]
    quality_assessor.assess.return_value = quality_report
    
    # Mock Path to exist
    monkeypatch.setattr(Path, "exists", lambda self: True)
    
    pipeline = VisionAnalysisPipeline(
        session=session,
        provider=MagicMock(),
        quality_assessor=quality_assessor,
        preprocessor=MagicMock(),
        entity_resolver=MagicMock()
    )
    
    await pipeline.run(1)
    
    assert analysis.status == ImageAnalysisStatus.FAILED
    assert "quality insufficient" in analysis.error_message
