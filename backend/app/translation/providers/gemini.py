"""Gemini translation (off-device; disabled unless ALLOW_OFF_DEVICE_PROVIDERS=true).

Instructed to translate faithfully and copy placeholders like ``[3]`` unchanged. Output is
validated by the same checks as every other provider.
"""

from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.translation.providers.base import LANGUAGE_NAMES, TranslationError

_SYSTEM = (
    "You are a professional agricultural translator for Indian government advisories. "
    "Translate faithfully. Do not add, remove, soften or explain anything. Keep every "
    "placeholder such as <0> or <1> exactly as written, placed where it belongs "
    "grammatically. Keep digits as digits. Return only a JSON array of strings, one "
    "translation per input, in the same order."
)


class GeminiTranslationProvider:
    provider_name = "gemini-translate"

    def __init__(self, api_key: str | None, model_name: str, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise TranslationError("GEMINI_API_KEY is not configured")
        self.model_version = model_name
        self._model = model_name
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    def supports(self, source_language: str, target_language: str) -> bool:
        return source_language in LANGUAGE_NAMES and target_language in LANGUAGE_NAMES

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        prompt = (
            f"Translate from {LANGUAGE_NAMES[source_language]} to "
            f"{LANGUAGE_NAMES[target_language]}.\nInput JSON array:\n"
            + json.dumps(texts, ensure_ascii=False)
        )
        try:
            resp = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema={"type": "ARRAY", "items": {"type": "STRING"}},
                ),
            )
            out = json.loads(resp.text or "[]")
        except Exception as exc:
            raise TranslationError(f"Gemini translation failed: {type(exc).__name__}") from exc
        if not isinstance(out, list) or len(out) != len(texts):
            raise TranslationError("Gemini returned a malformed translation batch")
        return [str(x) for x in out]
