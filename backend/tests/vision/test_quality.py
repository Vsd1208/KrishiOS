"""Tests for the QualityAssessor service."""

import pytest
from pathlib import Path
from PIL import Image

from app.vision.services.quality import QualityAssessor


@pytest.fixture
def temp_image(tmp_path):
    """Creates a temporary valid image file."""
    img_path = tmp_path / "test_image.jpg"
    img = Image.new("RGB", (800, 600), color="green")
    img.save(img_path)
    return img_path


def test_quality_assessor_accepts_good_image(monkeypatch, temp_image):
    class MockSettings:
        VISION_QUALITY_MIN_SCORE = 0.3
        
    monkeypatch.setattr("app.vision.services.quality.get_settings", lambda: MockSettings())
    
    assessor = QualityAssessor()
    report = assessor.assess(temp_image)
    
    assert report.usable is True
    assert report.score >= 0.3
    # Our simple green image might trigger some contrast issues in the basic proxy, but should still pass


def test_quality_assessor_rejects_dark_image(monkeypatch, tmp_path):
    class MockSettings:
        VISION_QUALITY_MIN_SCORE = 0.8
        
    monkeypatch.setattr("app.vision.services.quality.get_settings", lambda: MockSettings())
    
    dark_img_path = tmp_path / "dark.jpg"
    img = Image.new("RGB", (800, 600), color=(10, 10, 10))  # Very dark
    img.save(dark_img_path)
    
    assessor = QualityAssessor()
    report = assessor.assess(dark_img_path)
    
    assert report.usable is False
    assert any("too dark" in issue for issue in report.issues)
