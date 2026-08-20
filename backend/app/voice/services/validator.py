"""Audio validation service checking magic bytes, MIME, size, and duration."""

from dataclasses import dataclass
from typing import Any

from loguru import logger
from app.config.settings import get_settings


@dataclass(frozen=True, slots=True)
class AudioValidationResult:
    valid: bool
    mime_type: str
    file_size: int
    estimated_duration_seconds: float
    errors: list[str]


class AudioValidator:
    """Validates uploaded voice audio files for security, format, size, and duration."""

    MAGIC_BYTES = {
        "audio/wav": [b"RIFF"],
        "audio/x-wav": [b"RIFF"],
        "audio/mp3": [b"ID3", b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"],
        "audio/mpeg": [b"ID3", b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"],
        "audio/m4a": [b"\x00\x00\x00\x1cftypM4A", b"\x00\x00\x00\x20ftypM4A", b"ftypM4A", b"ftypisom", b"ftypmp42"],
        "audio/mp4": [b"\x00\x00\x00\x1cftyp", b"\x00\x00\x00\x20ftyp", b"ftypisom", b"ftypmp42"],
        "audio/ogg": [b"OggS"],
        "audio/webm": [b"\x1A\x45\xDF\xA3"],
    }

    def __init__(self) -> None:
        self.settings = get_settings()

    def validate(self, file_bytes: bytes, declared_mime: str | None = None) -> AudioValidationResult:
        """Run all validation checks on the raw audio file bytes."""
        errors: list[str] = []
        file_size = len(file_bytes)
        detected_mime = "unknown"

        # 1. Size validation
        max_bytes = self.settings.MAX_AUDIO_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            errors.append(f"Audio file exceeds maximum size of {self.settings.MAX_AUDIO_UPLOAD_SIZE_MB} MB.")
        if file_size == 0:
            errors.append("Audio file is empty.")
            return AudioValidationResult(False, detected_mime, file_size, 0.0, errors)

        # 2. Magic bytes MIME detection
        for mime, signatures in self.MAGIC_BYTES.items():
            for sig in signatures:
                if file_bytes.startswith(sig) or sig in file_bytes[:32]:
                    detected_mime = mime
                    break
            if detected_mime != "unknown":
                break

        # Fallback to declared MIME if magic bytes matching is ambiguous
        if detected_mime == "unknown" and declared_mime:
            clean_declared = declared_mime.split(";")[0].strip().lower()
            if clean_declared in self.settings.AUDIO_ALLOWED_MIMES:
                detected_mime = clean_declared

        if detected_mime not in self.settings.AUDIO_ALLOWED_MIMES and detected_mime == "unknown":
            errors.append(f"Unsupported audio format. Detected: {detected_mime}")

        # 3. Estimate duration (rough heuristic based on bitrate ~128kbps = 16KB/s)
        estimated_duration = max(1.0, round(file_size / 16000.0, 1))
        if estimated_duration > self.settings.MAX_AUDIO_DURATION_SECONDS:
            errors.append(
                f"Estimated audio duration ({estimated_duration}s) exceeds maximum allowed ({self.settings.MAX_AUDIO_DURATION_SECONDS}s)."
            )

        return AudioValidationResult(
            valid=len(errors) == 0,
            mime_type=detected_mime if detected_mime != "unknown" else (declared_mime or "audio/wav"),
            file_size=file_size,
            estimated_duration_seconds=estimated_duration,
            errors=errors,
        )
