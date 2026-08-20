"""Central registry managing STT and TTS provider instances."""

from loguru import logger
from app.voice.providers.stt_base import SpeechToTextProvider
from app.voice.providers.tts_base import TextToSpeechProvider


class VoiceProviderRegistry:
    """Registry managing available STT and TTS providers."""

    def __init__(self) -> None:
        self._stt_providers: dict[str, SpeechToTextProvider] = {}
        self._tts_providers: dict[str, TextToSpeechProvider] = {}

    def register_stt(self, provider: SpeechToTextProvider) -> None:
        name = provider.provider_name
        self._stt_providers[name] = provider
        logger.info("VoiceProviderRegistry: registered STT provider '{}' (v{})", name, provider.model_version)

    def register_tts(self, provider: TextToSpeechProvider) -> None:
        name = provider.provider_name
        self._tts_providers[name] = provider
        logger.info("VoiceProviderRegistry: registered TTS provider '{}' (v{})", name, provider.model_version)

    def get_stt(self, name: str) -> SpeechToTextProvider | None:
        return self._stt_providers.get(name)

    def get_tts(self, name: str) -> TextToSpeechProvider | None:
        return self._tts_providers.get(name)

    def list_stt(self) -> list[dict[str, str]]:
        return [{"name": p.provider_name, "version": p.model_version} for p in self._stt_providers.values()]

    def list_tts(self) -> list[dict[str, str]]:
        return [{"name": p.provider_name, "version": p.model_version} for p in self._tts_providers.values()]


# Global singleton instance
voice_provider_registry = VoiceProviderRegistry()
