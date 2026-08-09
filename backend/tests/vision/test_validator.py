"""Tests for the ImageValidator service."""

from io import BytesIO
from PIL import Image

from app.vision.services.validator import ImageValidator


def test_validator_accepts_valid_jpeg(monkeypatch):
    # Mock settings
    class MockSettings:
        MAX_IMAGE_UPLOAD_SIZE_MB = 15
        IMAGE_MAX_DIMENSION = 4096
        IMAGE_MIN_DIMENSION = 224
        IMAGE_ALLOWED_MIMES = ["image/jpeg", "image/png", "image/webp"]
        
    monkeypatch.setattr("app.vision.services.validator.get_settings", lambda: MockSettings())
    
    validator = ImageValidator()
    
    # Create a valid JPEG in memory
    img = Image.new("RGB", (800, 600), color="red")
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="JPEG")
    file_bytes = img_byte_arr.getvalue()
    
    result = validator.validate(file_bytes, "image/jpeg")
    
    assert result.valid is True
    assert result.mime_type == "image/jpeg"
    assert result.width == 800
    assert result.height == 600
    assert len(result.errors) == 0


def test_validator_rejects_oversized_file(monkeypatch):
    class MockSettings:
        MAX_IMAGE_UPLOAD_SIZE_MB = 1  # 1MB limit
        IMAGE_MAX_DIMENSION = 4096
        IMAGE_MIN_DIMENSION = 224
        IMAGE_ALLOWED_MIMES = ["image/jpeg"]
        
    monkeypatch.setattr("app.vision.services.validator.get_settings", lambda: MockSettings())
    validator = ImageValidator()
    
    file_bytes = b"\xFF\xD8\xFF" + b"0" * (2 * 1024 * 1024)  # 2MB fake file
    result = validator.validate(file_bytes, "image/jpeg")
    
    assert result.valid is False
    assert any("exceeds maximum size" in err for err in result.errors)


def test_validator_rejects_invalid_mime(monkeypatch):
    class MockSettings:
        MAX_IMAGE_UPLOAD_SIZE_MB = 15
        IMAGE_MAX_DIMENSION = 4096
        IMAGE_MIN_DIMENSION = 224
        IMAGE_ALLOWED_MIMES = ["image/jpeg"]
        
    monkeypatch.setattr("app.vision.services.validator.get_settings", lambda: MockSettings())
    validator = ImageValidator()
    
    # PDF magic bytes
    file_bytes = b"%PDF-1.4\n" + b"0" * 1024
    result = validator.validate(file_bytes, "application/pdf")
    
    assert result.valid is False
    assert any("Unsupported file format" in err for err in result.errors)
