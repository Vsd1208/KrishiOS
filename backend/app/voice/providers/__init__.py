# app/voice/providers/__init__.py
from app.voice.providers.mock_stt import MockSTTProvider
from app.voice.providers.mock_tts import MockTTSProvider
from app.voice.providers.registry import VoiceProviderRegistry, voice_provider_registry
from app.voice.providers.stt_base import LanguageDetectionResult, SpeechToTextProvider, STTResult
from app.voice.providers.tts_base import TextToSpeechProvider, TTSResult

__all__ = [
    "LanguageDetectionResult",
    "MockSTTProvider",
    "MockTTSProvider",
    "STTResult",
    "SpeechToTextProvider",
    "TTSResult",
    "TextToSpeechProvider",
    "VoiceProviderRegistry",
    "voice_provider_registry",
]
