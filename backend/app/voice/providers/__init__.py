# app/voice/providers/__init__.py
from app.voice.providers.stt_base import SpeechToTextProvider, STTResult, LanguageDetectionResult
from app.voice.providers.tts_base import TextToSpeechProvider, TTSResult
from app.voice.providers.mock_stt import MockSTTProvider
from app.voice.providers.mock_tts import MockTTSProvider
from app.voice.providers.registry import VoiceProviderRegistry, voice_provider_registry

__all__ = [
    "SpeechToTextProvider",
    "STTResult",
    "LanguageDetectionResult",
    "TextToSpeechProvider",
    "TTSResult",
    "MockSTTProvider",
    "MockTTSProvider",
    "VoiceProviderRegistry",
    "voice_provider_registry",
]
