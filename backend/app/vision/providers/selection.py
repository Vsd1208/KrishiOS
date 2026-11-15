"""Config-driven vision provider selection (Sprint 11)."""

from __future__ import annotations

from app.config.settings import get_settings
from app.providers import ProviderInfo, ProviderKind, ProviderSelector
from app.vision.providers.base import VisionModelProvider
from app.vision.providers.mock_provider import MockVisionProvider

vision_selector: ProviderSelector[VisionModelProvider] = ProviderSelector("vision")

vision_selector.register(
    ProviderInfo(
        capability="vision",
        name="mock-v1",
        version="0.1.0",
        kind=ProviderKind.MOCK,
        description="Canned findings chosen from the crop hint text, not from the image.",
    ),
    lambda: MockVisionProvider(model_name="mock-v1", model_version="0.1.0"),
)


def get_vision_provider() -> VisionModelProvider:
    """Return the provider named by ``VISION_PROVIDER``."""
    return vision_selector.get(get_settings().VISION_PROVIDER)


def get_vision_provider_info() -> ProviderInfo:
    return vision_selector.info(get_settings().VISION_PROVIDER)
