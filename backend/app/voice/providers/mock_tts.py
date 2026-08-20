"""Mock Text-to-Speech provider generating concise spoken audio responses."""

import asyncio
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.config.settings import get_settings
from app.voice.providers.tts_base import TTSResult


class MockTTSProvider:
    """Deterministic Text-to-Speech provider generating audio output files for testing."""

    def __init__(self, provider_name: str = "mock-tts-v1", model_version: str = "0.1.0") -> None:
        self._provider_name = provider_name
        self._model_version = model_version
        self._settings = get_settings()

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_version(self) -> str:
        return self._model_version

    async def synthesize(self, text: str, language: str) -> TTSResult:
        """Synthesize text into a dummy WAV file in AUDIO_STORAGE_PATH."""
        t0 = perf_counter()
        await asyncio.sleep(0.05)  # Simulate synthesis

        audio_uuid = uuid4()
        out_dir = Path(self._settings.AUDIO_STORAGE_PATH) / "tts"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{audio_uuid}.wav"

        # Write dummy WAV header + silence payload if file doesn't exist
        if not out_file.exists():
            # Minimum valid 44-byte RIFF WAV header + 100 bytes silence
            wav_header = (
                b"RIFF\x8c\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x68\x00\x00\x00"
            )
            out_file.write_bytes(wav_header + b"\x00" * 100)

        duration_sec = max(2.0, round(len(text) * 0.08, 1))
        inference_ms = (perf_counter() - t0) * 1000

        return TTSResult(
            audio_uuid=audio_uuid,
            audio_path=out_file,
            language=language,
            text_length=len(text),
            duration_seconds=duration_sec,
            model_name=self.provider_name,
            model_version=self.model_version,
            inference_ms=inference_ms,
        )

    async def health(self) -> bool:
        return True
