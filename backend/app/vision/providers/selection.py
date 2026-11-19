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


def _onnx() -> VisionModelProvider:
    from app.catalog.paths import artifacts_dir  # noqa: PLC0415
    from app.providers import ProviderConfigurationError  # noqa: PLC0415
    from app.vision.providers.onnx_crop_classifier import (  # noqa: PLC0415
        OnnxCropClassifier,
        latest_vision_artifact,
    )

    s = get_settings()
    art = latest_vision_artifact(artifacts_dir() / "vision", s.VISION_MODEL_VERSION)
    if art is None:
        raise ProviderConfigurationError(
            "onnx-crop-classifier: no exported model under ML_ARTIFACTS_DIR/vision")
    return OnnxCropClassifier(art, s.VISION_CROP_CONFIRM_THRESHOLD, s.VISION_AUTO_ACCEPT_CROP)


vision_selector.register(
    ProviderInfo(
        capability="vision",
        name="onnx-crop-classifier",
        version="artifact",
        kind=ProviderKind.LIVE,
        description="Local crop identification + disease model (ONNX, CPU); images stay on "
                    "the device. Low confidence or unsupported crop -> farmer confirms.",
    ),
    _onnx,
)


def get_vision_provider() -> VisionModelProvider:
    """Return the provider named by ``VISION_PROVIDER``."""
    return vision_selector.get(get_settings().VISION_PROVIDER)


def get_vision_provider_info() -> ProviderInfo:
    return vision_selector.info(get_settings().VISION_PROVIDER)
