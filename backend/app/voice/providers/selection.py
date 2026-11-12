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


def _whisper(size: str):
    def build() -> SpeechToTextProvider:
        from app.voice.providers.whisper_stt import FasterWhisperSTTProvider  # noqa: PLC0415

        return FasterWhisperSTTProvider(model_size=size)
    return build


def _gemini_stt() -> SpeechToTextProvider:
    from app.voice.providers.gemini_stt import GeminiSTTProvider  # noqa: PLC0415

    s = get_settings()
    return GeminiSTTProvider(s.GEMINI_API_KEY, s.LLM_MODEL, s.LLM_TIMEOUT_SECONDS)


def _mms_tts() -> TextToSpeechProvider:
    from app.voice.providers.mms_tts import MMSTTSProvider  # noqa: PLC0415

    return MMSTTSProvider()


for _size in ("small", "medium", "large-v3"):
    stt_selector.register(
        ProviderInfo("stt", f"faster-whisper-{_size}", f"{_size}-int8", ProviderKind.LIVE,
                     description="Local Whisper (MIT) on CPU; LID restricted to en/hi/te."),
        _whisper(_size),
    )
stt_selector.register(
    ProviderInfo("stt", "gemini-stt", get_settings().LLM_MODEL, ProviderKind.LIVE,
                 sends_data_off_device=True,
                 description="Gemini audio transcription (farmer audio leaves the device)."),
    _gemini_stt,
)
tts_selector.register(
    ProviderInfo("tts", "mms-tts", "facebook-mms-1b-vits", ProviderKind.LIVE,
                 description="Local Meta MMS-TTS (VITS). Licence CC BY-NC 4.0: "
                             "non-commercial, research/demo only."),
    _mms_tts,
)


def get_stt_provider() -> SpeechToTextProvider:
    return stt_selector.get(get_settings().STT_PROVIDER)


def get_tts_provider() -> TextToSpeechProvider:
    return tts_selector.get(get_settings().TTS_PROVIDER)
