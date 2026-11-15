"""Gemini audio transcription (off-device; opt-in via ALLOW_OFF_DEVICE_PROVIDERS).

Used as a comparison baseline and fallback. Farmer audio is personal data (DPDP): this
provider only runs when explicitly allowed, and the provider info discloses it.
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path
from time import perf_counter

from google import genai
from google.genai import types

from app.catalog.text import script_of, tokenize
from app.voice.providers.stt_base import LanguageDetectionResult, STTResult

_SCRIPT = {"te": "Telugu", "hi": "Devanagari", "en": "Latin"}
_PROMPT = (
    "Transcribe this farmer's speech verbatim in its original script (Telugu in Telugu "
    "script, Hindi in Devanagari, English words in Latin script as spoken). Do not translate "
    "or correct. Return JSON with fields transcript and language (one of en, hi, te)."
)


class GeminiSTTProvider:
    provider_name = "gemini-stt"

    def __init__(self, api_key: str | None, model_name: str, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self._model = model_name
        self.model_version = model_name
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
        )

    async def transcribe(self, audio_path: Path, hint_language: str | None = None) -> STTResult:
        t0 = perf_counter()
        mime = mimetypes.guess_type(audio_path.name)[0] or "audio/wav"
        audio = await asyncio.to_thread(audio_path.read_bytes)
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[types.Part.from_bytes(data=audio, mime_type=mime),
                      _PROMPT + (f" Expected language: {hint_language}." if hint_language else "")],
            config=types.GenerateContentConfig(
                temperature=0.0, response_mime_type="application/json",
                response_schema={"type": "OBJECT", "properties": {
                    "transcript": {"type": "STRING"},
                    "language": {"type": "STRING", "enum": ["en", "hi", "te"]}},
                    "required": ["transcript", "language"]},
            ),
        )
        data = json.loads(resp.text or "{}")
        text = str(data.get("transcript", "")).strip()
        lang = data.get("language") if data.get("language") in _SCRIPT else (hint_language or "en")
        scripts = {script_of(t) for t in tokenize(text)}
        ms = (perf_counter() - t0) * 1000
        return STTResult(
            raw_transcript=text, detected_language=lang, language_confidence=0.0,
            transcription_confidence=0.0,  # Gemini exposes no calibrated confidence
            model_name=self.provider_name, model_version=self.model_version, inference_ms=ms,
            is_code_switched="latin" in scripts and bool(scripts & {"telugu", "devanagari"}),
            language_detection=LanguageDetectionResult(lang, 0.0, _SCRIPT[lang]),
            metadata={"confidence_available": False},
        )

    async def detect_language(self, audio_path: Path) -> LanguageDetectionResult:
        res = await self.transcribe(audio_path)
        return res.language_detection or LanguageDetectionResult(res.detected_language, 0.0, "")

    async def health(self) -> bool:
        return True
