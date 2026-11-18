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
    # Sprint 11, Phase 9: what crop is in the photo. ``crop_candidates`` are (crop key,
    # calibrated probability), best first; the key is a catalog ``crop_canonical`` or, for a
    # recognised crop outside the catalog, ``other:<label>``. ``crop_supported`` is true only
    # when the top crop is a catalog crop the model supports and is confident enough; when
    # false, the farmer is asked to confirm the crop (never a silent guess).
    crop_candidates: list[tuple[str, float]] = field(default_factory=list)
    crop_supported: bool = False


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
