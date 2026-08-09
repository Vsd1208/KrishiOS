"""Image validation service (MIME, size, dimensions, corruption check)."""

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from loguru import logger
from PIL import Image, UnidentifiedImageError

from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    mime_type: str
    width: int
    height: int
    errors: list[str]


class ImageValidator:
    """Validates uploaded images for security and compliance."""

    MAGIC_BYTES = {
        "image/jpeg": [b"\xFF\xD8\xFF"],
        "image/png": [b"\x89\x50\x4E\x47"],
        "image/webp": [b"\x52\x49\x46\x46"],
    }

    def __init__(self) -> None:
        self.settings = get_settings()

    def validate(self, file_bytes: bytes, declared_mime: str | None = None) -> ValidationResult:
        """Run all validation checks on the raw file bytes."""
        errors = []
        width, height = 0, 0
        detected_mime = "unknown"

        # 1. Size validation
        max_bytes = self.settings.MAX_IMAGE_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            errors.append(f"File exceeds maximum size of {self.settings.MAX_IMAGE_UPLOAD_SIZE_MB} MB.")
        if len(file_bytes) == 0:
            errors.append("File is empty.")
            return ValidationResult(False, detected_mime, width, height, errors)

        # 2. Magic bytes MIME detection
        for mime, signatures in self.MAGIC_BYTES.items():
            for sig in signatures:
                if file_bytes.startswith(sig):
                    detected_mime = mime
                    break
            if detected_mime != "unknown":
                break

        if detected_mime not in self.settings.IMAGE_ALLOWED_MIMES:
            errors.append(f"Unsupported file format. Detected: {detected_mime}")

        # 3. Pillow validation (corrupted image + dimensions)
        if not errors:
            try:
                with Image.open(BytesIO(file_bytes)) as img:
                    img.verify()  # Fast check for corruption
                    width, height = img.size
                    
                    if width > self.settings.IMAGE_MAX_DIMENSION or height > self.settings.IMAGE_MAX_DIMENSION:
                        errors.append(f"Dimensions {width}x{height} exceed maximum {self.settings.IMAGE_MAX_DIMENSION}px.")
                    
                    if width < self.settings.IMAGE_MIN_DIMENSION or height < self.settings.IMAGE_MIN_DIMENSION:
                        errors.append(f"Dimensions {width}x{height} below minimum {self.settings.IMAGE_MIN_DIMENSION}px.")
            
            except UnidentifiedImageError:
                errors.append("File is corrupted or not a valid image.")
            except Exception as e:
                logger.warning("ImageValidator: Pillow validation failed: {}", e)
                errors.append("Failed to process image.")

        return ValidationResult(
            valid=len(errors) == 0,
            mime_type=detected_mime,
            width=width,
            height=height,
            errors=errors,
        )
