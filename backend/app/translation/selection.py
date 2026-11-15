"""Config-driven translation provider selection (Sprint 11)."""

from __future__ import annotations

from app.config.settings import get_settings
from app.providers import ProviderInfo, ProviderKind, ProviderSelector
from app.providers.status import register_capability
from app.translation.providers.base import TranslationProvider
from app.translation.providers.indictrans2 import IndicTrans2Provider
from app.translation.providers.mock import MockTranslationProvider
from app.translation.providers.opus_mt import OpusMTProvider

translation_selector: ProviderSelector[TranslationProvider] = ProviderSelector("translation")


def _gemini() -> TranslationProvider:
    from app.translation.providers.gemini import GeminiTranslationProvider  # noqa: PLC0415

    s = get_settings()
    return GeminiTranslationProvider(s.GEMINI_API_KEY, s.LLM_MODEL, s.LLM_TIMEOUT_SECONDS)


translation_selector.register(
    ProviderInfo("translation", "mock-translation", "0.1.0", ProviderKind.MOCK,
                 description="Tags the source text; no translation happens."),
    MockTranslationProvider,
)
translation_selector.register(
    ProviderInfo("translation", "opus-mt", OpusMTProvider.model_version, ProviderKind.LIVE,
                 description="Local Helsinki-NLP Marian models (Apache-2.0); interim, "
                             "lower quality than IndicTrans2."),
    OpusMTProvider,
)
translation_selector.register(
    ProviderInfo("translation", "indictrans2", IndicTrans2Provider.model_version,
                 ProviderKind.LIVE,
                 description="Local AI4Bharat IndicTrans2 distilled (MIT). Gated on Hugging Face."),
    IndicTrans2Provider,
)
translation_selector.register(
    ProviderInfo("translation", "gemini-translate", get_settings().LLM_MODEL, ProviderKind.LIVE,
                 sends_data_off_device=True,
                 description="Google Gemini (text leaves the device)."),
    _gemini,
)

register_capability(
    "translation", lambda s: s.TRANSLATION_PROVIDER, lambda: translation_selector
)
register_capability(
    "translation_fallback", lambda s: s.TRANSLATION_FALLBACK_PROVIDER,
    lambda: translation_selector,
)
