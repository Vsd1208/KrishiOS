"""Local Helsinki-NLP opus-mt (Marian) translation. Apache-2.0, runs on CPU.

Interim local option while IndicTrans2 (gated on Hugging Face) awaits access.
Telugu uses the multilingual Dravidian models (``opus-mt-en-dra`` with a ``>>tel<<``
target token, and ``opus-mt-dra-en``). Requires the ``local-ml`` extra (sentencepiece).
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.providers.device import resolve_device
from app.translation.providers.base import TranslationError

_MODELS: dict[tuple[str, str], tuple[str, str | None]] = {
    ("en", "hi"): ("Helsinki-NLP/opus-mt-en-hi", None),
    ("hi", "en"): ("Helsinki-NLP/opus-mt-hi-en", None),
    ("en", "te"): ("Helsinki-NLP/opus-mt-en-dra", ">>tel<<"),
    ("te", "en"): ("Helsinki-NLP/opus-mt-dra-en", None),
}


class OpusMTProvider:
    provider_name = "opus-mt"
    model_version = "helsinki-nlp-opus-2020"

    def __init__(self, max_new_tokens: int = 256, num_beams: int = 4) -> None:
        self._max_new_tokens = max_new_tokens
        self._num_beams = num_beams
        self._loaded: dict[str, tuple[Any, Any]] = {}

    def supports(self, source_language: str, target_language: str) -> bool:
        return (source_language, target_language) in _MODELS

    def _load(self, model_id: str) -> tuple[Any, Any]:
        if model_id not in self._loaded:
            try:
                from transformers import MarianMTModel, MarianTokenizer  # noqa: PLC0415

                tok = MarianTokenizer.from_pretrained(model_id)
                model = MarianMTModel.from_pretrained(model_id)
            except Exception as exc:
                raise TranslationError(f"cannot load {model_id}: {type(exc).__name__}") from exc
            model.eval().to(resolve_device())
            self._loaded[model_id] = (tok, model)
            logger.info("opus-mt model loaded | {}", model_id)
        return self._loaded[model_id]

    def _translate_sync(self, texts: list[str], src: str, tgt: str) -> list[str]:
        import torch  # noqa: PLC0415

        model_id, prefix = _MODELS[(src, tgt)]
        tok, model = self._load(model_id)
        inputs = [f"{prefix} {t}" if prefix else t for t in texts]
        batch = tok(inputs, return_tensors="pt", padding=True, truncation=True,
                    max_length=512).to(resolve_device())
        with torch.inference_mode():
            out = model.generate(
                **batch, max_new_tokens=self._max_new_tokens, num_beams=self._num_beams
            )
        return [tok.decode(o, skip_special_tokens=True) for o in out]

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        if not self.supports(source_language, target_language):
            raise TranslationError(
                f"opus-mt does not support {source_language}->{target_language}"
            )
        return await asyncio.to_thread(
            self._translate_sync, texts, source_language, target_language
        )
