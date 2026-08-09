"""Base protocol and types for vision model providers."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Observation:
    """A specific visual finding from the image."""
    finding: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None


@dataclass(frozen=True, slots=True)
class Condition:
    """A candidate disease, pest, or nutrient deficiency."""
    name: str
    confidence: float


@dataclass(frozen=True, slots=True)
class VisionResult:
    """Standardized output from any vision model provider."""
    crop_detected: str | None
    observations: list[Observation]
    candidate_conditions: list[Condition]
    model_name: str
    model_version: str
    inference_ms: float
    metadata: dict = field(default_factory=dict)


class VisionModelProvider(Protocol):
    """Protocol for crop vision model integrations."""

    @property
    def model_name(self) -> str:
        """Name of the model provider."""
        ...

    @property
    def model_version(self) -> str:
        """Version of the model being used."""
        ...

    async def analyze(self, image_path: Path, metadata: dict) -> VisionResult:
        """Analyze an image and return structured findings."""
        ...

    async def health(self) -> bool:
        """Check if the model provider is healthy and accessible."""
        ...
