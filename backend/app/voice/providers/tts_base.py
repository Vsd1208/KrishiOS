"""Text-to-speech provider protocol and data contracts."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class TTSResult:
    """Standardized output from speech synthesis."""
    audio_uuid: UUID
    audio_path: Path
    language: str
    text_length: int
    duration_seconds: float
    model_name: str
    model_version: str
    inference_ms: float
    metadata: dict = field(default_factory=dict)


class TextToSpeechProvider(Protocol):
    """Protocol contract for text-to-speech synthesis engines."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_version(self) -> str:
        ...

    async def synthesize(self, text: str, language: str) -> TTSResult:
        ...

    async def health(self) -> bool:
        ...
