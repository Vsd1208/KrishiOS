"""Mock vision provider for testing and MVP."""

import asyncio
from pathlib import Path
from time import perf_counter

from app.vision.providers.base import Condition, Observation, VisionResult


class MockVisionProvider:
    """Deterministic mock provider for end-to-end testing without GPU."""

    def __init__(self, model_name: str = "mock-v1", model_version: str = "0.1.0") -> None:
        self._model_name = model_name
        self._model_version = model_version

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    async def analyze(self, image_path: Path, metadata: dict) -> VisionResult:
        """Return deterministic findings based on the crop hint."""
        t0 = perf_counter()
        
        # Simulate inference delay
        await asyncio.sleep(0.5)
        
        crop_hint = str(metadata.get("crop_hint", "")).lower()
        
        if "paddy" in crop_hint or "rice" in crop_hint:
            crop_detected = "Paddy"
            observations = [
                Observation(finding="yellowing leaves", confidence=0.88),
                Observation(finding="brown lesions with yellow halo", confidence=0.75),
            ]
            candidates = [
                Condition(name="Brown Spot", confidence=0.82),
                Condition(name="Bacterial Leaf Blight", confidence=0.61),
            ]
        elif "cotton" in crop_hint:
            crop_detected = "Cotton"
            observations = [
                Observation(finding="curled leaves", confidence=0.91),
                Observation(finding="white insects on underside", confidence=0.85),
            ]
            candidates = [
                Condition(name="Whitefly Infestation", confidence=0.89),
                Condition(name="Cotton Leaf Curl Virus", confidence=0.45),
            ]
        elif "tomato" in crop_hint:
            crop_detected = "Tomato"
            observations = [
                Observation(finding="dark concentric rings on lower leaves", confidence=0.92),
                Observation(finding="yellowing lower foliage", confidence=0.78),
            ]
            candidates = [
                Condition(name="Early Blight", confidence=0.94),
                Condition(name="Septoria Leaf Spot", confidence=0.55),
            ]
        else:
            # Generic response for unknown crops or missing hint
            crop_detected = "Unknown"
            observations = [
                Observation(finding="chlorosis on leaves", confidence=0.60),
                Observation(finding="stunted growth", confidence=0.50),
            ]
            candidates = [
                Condition(name="Nitrogen Deficiency", confidence=0.55),
                Condition(name="General Stress", confidence=0.40),
            ]

        inference_ms = (perf_counter() - t0) * 1000

        return VisionResult(
            crop_detected=crop_detected,
            observations=observations,
            candidate_conditions=candidates,
            model_name=self.model_name,
            model_version=self.model_version,
            inference_ms=inference_ms,
        )

    async def health(self) -> bool:
        """Mock provider is always healthy."""
        return True
