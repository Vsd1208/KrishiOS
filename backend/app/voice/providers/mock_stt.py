"""Mock Speech-to-Text provider supporting English, Hindi, Telugu, and Code-Switching."""

import asyncio
from pathlib import Path
from time import perf_counter

from app.voice.providers.stt_base import LanguageDetectionResult, STTResult


class MockSTTProvider:
    """Deterministic Speech-to-Text provider for testing and MVP execution."""

    def __init__(self, provider_name: str = "mock-stt-v1", model_version: str = "0.1.0") -> None:
        self._provider_name = provider_name
        self._model_version = model_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_version(self) -> str:
        return self._model_version

    async def detect_language(self, audio_path: Path) -> LanguageDetectionResult:
        """Detect language from filename hints or default to hint."""
        fname = audio_path.name.lower()
        if "te" in fname or "telugu" in fname:
            return LanguageDetectionResult(language_code="te", confidence=0.96, script="Telugu")
        elif "hi" in fname or "hindi" in fname:
            return LanguageDetectionResult(language_code="hi", confidence=0.95, script="Devanagari")
        elif "mixed" in fname or "codeswitch" in fname:
            return LanguageDetectionResult(language_code="te", confidence=0.88, script="Telugu/Latin")
        else:
            return LanguageDetectionResult(language_code="en", confidence=0.98, script="Latin")

    async def transcribe(self, audio_path: Path, hint_language: str | None = None) -> STTResult:
        """Transcribe audio file deterministically based on hint_language or filename."""
        t0 = perf_counter()
        await asyncio.sleep(0.1)  # Simulate ASR processing

        fname = audio_path.name.lower()
        lang = hint_language or "en"
        
        if "te" in fname or "telugu" in fname or lang == "te":
            transcript = "నా వరి పైరుకు అగ్గి తెగులు వచ్చింది, ఏమి చేయాలి?"
            det_lang = "te"
            lang_conf = 0.96
            script = "Telugu"
            is_code_switched = False
        elif "hi" in fname or "hindi" in fname or lang == "hi":
            transcript = "धान की फसल में भूरा धब्बा रोग का इलाज क्या है?"
            det_lang = "hi"
            lang_conf = 0.95
            script = "Devanagari"
            is_code_switched = False
        elif "mixed" in fname or "codeswitch" in fname or lang == "mixed":
            transcript = "నా వరి crop కి yellow spots వస్తున్నాయి"
            det_lang = "te"
            lang_conf = 0.90
            script = "Telugu/Latin"
            is_code_switched = True
        elif "low_conf" in fname or lang == "low_conf":
            transcript = "muffled audio noise background"
            det_lang = "en"
            lang_conf = 0.35
            script = "Latin"
            is_code_switched = False
        else:
            transcript = "What is the best fertilizer for wheat in Rabi season?"
            det_lang = "en"
            lang_conf = 0.98
            script = "Latin"
            is_code_switched = False

        duration_ms = (perf_counter() - t0) * 1000
        lid_res = LanguageDetectionResult(
            language_code=det_lang,
            confidence=lang_conf,
            script=script,
            detected_at_ms=duration_ms * 0.2,
        )

        return STTResult(
            raw_transcript=transcript,
            detected_language=det_lang,
            language_confidence=lang_conf,
            transcription_confidence=0.35 if lang == "low_conf" else 0.92,
            model_name=self.provider_name,
            model_version=self.model_version,
            inference_ms=duration_ms,
            is_code_switched=is_code_switched,
            language_detection=lid_res,
        )

    async def health(self) -> bool:
        return True
