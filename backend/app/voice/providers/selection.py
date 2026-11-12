"""Config-driven STT/TTS provider selection (Sprint 11)."""

from __future__ import annotations

from app.config.settings import get_settings
from app.providers import ProviderInfo, ProviderKind, ProviderSelector
from app.voice.providers.mock_stt import MockSTTProvider
from app.voice.providers.mock_tts import MockTTSProvider
from app.voice.providers.stt_base import SpeechToTextProvider
from app.voice.providers.tts_base import TextToSpeechProvider

stt_selector: ProviderSelector[SpeechToTextProvider] = ProviderSelector("stt")
tts_selector: ProviderSelector[TextToSpeechProvider] = ProviderSelector("tts")

stt_selector.register(
    ProviderInfo(
        capability="stt",
        name="mock-stt-v1",
        version="0.1.0",
        kind=ProviderKind.MOCK,
        description="Canned transcripts chosen from the filename / language hint (tests only).",
    ),
    MockSTTProvider,
)
tts_selector.register(
    ProviderInfo(
        capability="tts",
        name="mock-tts-v1",
        version="0.1.0",
        kind=ProviderKind.MOCK,
        description="Writes a silent placeholder file (tests only).",
    ),
    MockTTSProvider,
)


def get_stt_provider() -> SpeechToTextProvider:
    return stt_selector.get(get_settings().STT_PROVIDER)


def get_tts_provider() -> TextToSpeechProvider:
    return tts_selector.get(get_settings().TTS_PROVIDER)
