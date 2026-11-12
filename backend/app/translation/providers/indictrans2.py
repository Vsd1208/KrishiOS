"""Local AI4Bharat IndicTrans2 distilled models (MIT). Recommended primary.

The checkpoints are **gated** on Hugging Face (accept the terms with an account, then set
``HF_TOKEN``). Until then loading fails, this provider raises ``TranslationError`` and the
service uses the configured fallback. Uses ``IndicTransToolkit`` pre/post-processing when
installed; otherwise the language-tag prefix documented on the model card.

Status: NOT YET VERIFIED against the real checkpoints (no access in this environment).
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.providers.hf import ensure_hf_token
from app.translation.providers.base import TranslationError

_TAGS = {"en": "eng_Latn", "hi": "hin_Deva", "te": "tel_Telu"}
_MODELS = {
    "en-indic": "ai4bharat/indictrans2-en-indic-dist-200M",
    "indic-en": "ai4bharat/indictrans2-indic-en-dist-200M",
}


class IndicTrans2Provider:
    provider_name = "indictrans2"
    model_version = "dist-200M"

    def __init__(self, max_new_tokens: int = 256, num_beams: int = 5) -> None:
        self._max_new_tokens = max_new_tokens
        self._num_beams = num_beams
        self._loaded: dict[str, tuple[Any, Any]] = {}

    def supports(self, source_language: str, target_language: str) -> bool:
        pair = {source_language, target_language}
        return "en" in pair and pair <= set(_TAGS) and source_language != target_language

    def _load(self, direction: str) -> tuple[Any, Any]:
        if direction not in self._loaded:
            model_id = _MODELS[direction]
            ensure_hf_token()
            try:
                from transformers import (  # noqa: PLC0415
                    AutoModelForSeq2SeqLM,
                    AutoTokenizer,
                )

                tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_id, trust_remote_code=True)
            except Exception as exc:
                raise TranslationError(
                    f"IndicTrans2 unavailable ({type(exc).__name__}); the checkpoints are gated "
                    "on Hugging Face: accept the terms and set HF_TOKEN"
                ) from exc
            model.eval()
            self._loaded[direction] = (tok, model)
            logger.info("IndicTrans2 loaded | {}", model_id)
        return self._loaded[direction]

    def _translate_sync(self, texts: list[str], src: str, tgt: str) -> list[str]:
        import torch  # noqa: PLC0415

        direction = "en-indic" if src == "en" else "indic-en"
        tok, model = self._load(direction)
        try:
            from IndicTransToolkit import IndicProcessor  # noqa: PLC0415

            ip = IndicProcessor(inference=True)
            batch_in = ip.preprocess_batch(texts, src_lang=_TAGS[src], tgt_lang=_TAGS[tgt])
        except ImportError:
            ip = None
            batch_in = [f"{_TAGS[src]} {_TAGS[tgt]} {t}" for t in texts]
        enc = tok(batch_in, truncation=True, padding="longest", return_tensors="pt")
        with torch.inference_mode():
            out = model.generate(
                **enc, max_new_tokens=self._max_new_tokens, num_beams=self._num_beams
            )
        decoded = tok.batch_decode(out, skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True)
        if ip is not None:
            decoded = ip.postprocess_batch(decoded, lang=_TAGS[tgt])
        return decoded

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        if not self.supports(source_language, target_language):
            raise TranslationError(f"unsupported pair {source_language}->{target_language}")
        return await asyncio.to_thread(
            self._translate_sync, texts, source_language, target_language
        )
