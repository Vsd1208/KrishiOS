"""Tests for the MockVisionProvider."""

import pytest
from pathlib import Path
from app.vision.providers.mock_provider import MockVisionProvider


@pytest.mark.asyncio
async def test_mock_provider_paddy():
    provider = MockVisionProvider()
    result = await provider.analyze(Path("dummy.jpg"), {"crop_hint": "paddy"})
    
    assert result.crop_detected == "Paddy"
    assert len(result.observations) > 0
    assert len(result.candidate_conditions) > 0
    assert any(c.name == "Brown Spot" for c in result.candidate_conditions)


@pytest.mark.asyncio
async def test_mock_provider_unknown():
    provider = MockVisionProvider()
    result = await provider.analyze(Path("dummy.jpg"), {"crop_hint": "unknown_crop"})
    
    assert result.crop_detected == "Unknown"
