"""Aggregate view of the active provider for every capability.

Used by ``GET /api/v1/providers`` (UI provider badges) and by the startup guard that
forbids mock providers in production.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.config.settings import Settings, get_settings
from app.providers.base import ProviderInfo, ProviderKind
from app.providers.selection import ProviderConfigurationError, ProviderSelector


@dataclass(frozen=True, slots=True)
class ActiveProvider:
    """The configured provider for one capability (``info`` is None if unavailable)."""

    capability: str
    configured: str | None
    info: ProviderInfo | None
    error: str | None = None


# capability -> (setting reader, selector loader). Loaders import lazily so this module
# never pulls heavy provider code at import time.
SettingReader = Callable[[Settings], str | None]
SelectorLoader = Callable[[], ProviderSelector]
_CAPABILITIES: dict[str, tuple[SettingReader, SelectorLoader]] = {}


def register_capability(
    capability: str,
    setting: Callable[[Settings], str | None],
    selector_loader: Callable[[], ProviderSelector],
) -> None:
    """Register a capability for status reporting (idempotent)."""
    _CAPABILITIES[capability] = (setting, selector_loader)


def _llm_info(settings: Settings) -> ActiveProvider:
    name = settings.LLM_PROVIDER
    if name == "gemini":
        info = ProviderInfo("llm", "gemini", settings.LLM_MODEL, ProviderKind.LIVE,
                            sends_data_off_device=True,
                            description="Google Gemini API (prompts leave the device).")
    else:
        info = ProviderInfo("llm", "local", "krishios-local-v1", ProviderKind.MOCK,
                            description="Deterministic template responder (no real LLM).")
    return ActiveProvider("llm", name, info)


def _notification_infos(settings: Settings) -> list[ActiveProvider]:
    # All channels are in-memory sandboxes until the Phase 4/5 channel adapters land.
    return [
        ActiveProvider(
            f"notification:{channel}",
            channel,
            ProviderInfo(f"notification:{channel}", "in-memory-v1", "1.0.0", ProviderKind.SANDBOX,
                         description="In-process delivery record; nothing reaches a device."),
        )
        for channel in settings.NOTIFICATION_CHANNELS
    ]


def _register_builtin() -> None:
    def vision() -> ProviderSelector:
        from app.vision.providers.selection import vision_selector  # noqa: PLC0415
        return vision_selector

    def stt() -> ProviderSelector:
        from app.voice.providers.selection import stt_selector  # noqa: PLC0415
        return stt_selector

    def tts() -> ProviderSelector:
        from app.voice.providers.selection import tts_selector  # noqa: PLC0415
        return tts_selector

    def live(name: str) -> Callable[[], ProviderSelector]:
        def load() -> ProviderSelector:
            from app.live_data.providers import registry  # noqa: PLC0415
            return getattr(registry, f"{name}_selector")
        return load

    register_capability("vision", lambda s: s.VISION_PROVIDER, vision)
    register_capability("stt", lambda s: s.STT_PROVIDER, stt)
    register_capability("tts", lambda s: s.TTS_PROVIDER, tts)
    register_capability("weather", lambda s: s.WEATHER_PROVIDER_NAME, live("weather"))
    register_capability("market", lambda s: s.MARKET_PROVIDER_NAME, live("market"))
    register_capability("advisory", lambda s: s.ADVISORY_PROVIDER_NAME, live("advisory"))
    register_capability("scheme", lambda s: s.SCHEME_PROVIDER_NAME, live("scheme"))


_register_builtin()


def _ensure_optional_capabilities() -> None:
    """Import modules that register capabilities on import (translation, NLU)."""
    for module in ("app.translation.selection", "app.nlu.selection", "app.channels.providers",
                   "app.dpi.providers"):
        try:
            __import__(module)
        except ImportError:  # module not built yet
            continue


def active_providers(settings: Settings | None = None) -> list[ActiveProvider]:
    """Resolve the configured provider for every registered capability."""
    _ensure_optional_capabilities()
    settings = settings or get_settings()
    result = [_llm_info(settings)]
    for capability, (setting, loader) in sorted(_CAPABILITIES.items()):
        configured = setting(settings)
        if configured is None:
            result.append(ActiveProvider(capability, None, None, "not configured"))
            continue
        try:
            result.append(ActiveProvider(capability, configured, loader().info(configured)))
        except (ProviderConfigurationError, ImportError) as exc:
            result.append(ActiveProvider(capability, configured, None, str(exc)))
    result.extend(_notification_infos(settings))
    return result


def check_provider_policy(settings: Settings | None = None) -> list[str]:
    """Return policy violations; callers decide whether to fail startup.

    - unknown provider names are always violations;
    - mocks are violations when ``ALLOW_MOCK_PROVIDERS`` is false;
    - off-device providers are violations unless ``ALLOW_OFF_DEVICE_PROVIDERS`` is true.
    """
    settings = settings or get_settings()
    problems: list[str] = []
    for ap in active_providers(settings):
        if ap.error and ap.configured is not None:
            problems.append(f"{ap.capability}: {ap.error}")
            continue
        if ap.info is None:
            continue
        if ap.info.is_mock and not settings.ALLOW_MOCK_PROVIDERS:
            problems.append(f"{ap.capability}: mock provider {ap.info.name!r} not allowed")
        if (
            ap.info.sends_data_off_device
            and ap.capability != "llm"
            and not settings.ALLOW_OFF_DEVICE_PROVIDERS
        ):
            problems.append(
                f"{ap.capability}: {ap.info.name!r} sends data off-device; "
                "set ALLOW_OFF_DEVICE_PROVIDERS=true to opt in"
            )
    return problems
