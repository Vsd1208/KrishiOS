"""Tests for the ImagePreprocessor service."""

import pytest
from pathlib import Path
from PIL import Image

from app.vision.services.preprocessor import ImagePreprocessor


@pytest.fixture
def temp_image(tmp_path):
    img_path = tmp_path / "test_pre.jpg"
    img = Image.new("RGB", (1000, 500), color="blue")
    img.save(img_path)
    return img_path


def test_preprocessor_resizes_and_pads(temp_image):
    preprocessor = ImagePreprocessor()
    
    out_path = preprocessor.preprocess(temp_image, target_size=(224, 224))
    
    assert out_path.exists()
    assert out_path.name.endswith(".preprocessed.jpg")
    
    with Image.open(out_path) as out_img:
        assert out_img.size == (224, 224)
        assert out_img.mode == "RGB"
