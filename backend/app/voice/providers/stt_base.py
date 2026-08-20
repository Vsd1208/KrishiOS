"""Speech-to-text provider protocol and data contracts."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LanguageDetectionResult:
    """Output from language identification."""
    language_code: str  # e.g., "en", "hi", "te"
    confidence: float
    script: str  # e.g., "Latin", "Devanagari", "Telugu"
    detected_at_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class STTResult:
    """Standardized response from speech recognition."""
    raw_transcript: str
    detected_language: str
    language_confidence: float
    transcription_confidence: float
    model_name: str
    model_version: str
    inference_ms: float
    is_code_switched: bool = False
    language_detection: LanguageDetectionResult | None = None
    metadata: dict = field(default_factory=dict)


class SpeechToTextProvider(Protocol):
    """Protocol contract for speech-to-text recognition systems."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_version(self) -> str:
        ...

    async def transcribe(self, audio_path: Path, hint_language: str | None = None) -> STTResult:
        ...

    async def detect_language(self, audio_path: Path) -> LanguageDetectionResult:
        ...

    async def health(self) -> bool:
        ...
