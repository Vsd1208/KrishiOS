"""Local AI4Bharat IndicTrans2 distilled models (MIT). Recommended primary.

The checkpoints are **gated** on Hugging Face (accept the terms with an account, then set
``HF_TOKEN``). Until then loading fails, this provider raises ``TranslationError`` and the
service uses the configured fallback. Uses ``IndicTransToolkit`` pre/post-processing when
installed; otherwise the language-tag prefix documented on the model card.

IndicTrans2 is trained on script-unified text: Indic languages are written in Devanagari
internally. Without IndicTransToolkit (it needs a native build on Windows), Telugu input is
transliterated to Devanagari and Telugu output back to Telugu (``app.translation.script``).

KV cache: the checkpoint's bundled modelling code expects legacy tuple caches, while
transformers >= 4.5x passes Cache objects. ``_legacy_cache_adapter`` converts them (empty ->
None, otherwise ``to_legacy_cache()``). Verified on real advisory sentences to give outputs
identical to ``use_cache=False`` (greedy and 4 beams) while running 4.7-7.8x faster.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.config.settings import get_settings
from app.providers.hf import ensure_hf_token
from app.translation.providers.base import TranslationError
from app.translation.script import devanagari_to_telugu, telugu_to_devanagari

_TAGS = {"en": "eng_Latn", "hi": "hin_Deva", "te": "tel_Telu"}
_MODELS = {
    "en-indic": "ai4bharat/indictrans2-en-indic-dist-200M",
    "indic-en": "ai4bharat/indictrans2-indic-en-dist-200M",
}


def _legacy_cache_adapter(model: Any) -> None:
    """Make the legacy-tuple-cache model code work with transformers' Cache objects."""
    from transformers.cache_utils import Cache  # noqa: PLC0415

    original = model.prepare_inputs_for_generation

    def prepare(decoder_input_ids: Any, past_key_values: Any = None, **kwargs: Any) -> Any:
        if isinstance(past_key_values, Cache):
            past_key_values = (
                None if past_key_values.get_seq_length() == 0
                else past_key_values.to_legacy_cache()
            )
        return original(decoder_input_ids, past_key_values=past_key_values, **kwargs)

    model.prepare_inputs_for_generation = prepare


class IndicTrans2Provider:
    provider_name = "indictrans2"
    model_version = "dist-200M"
    # ">" is not in the source vocabulary; "<ID{i}>" returns as "<ID{i}", which restore accepts.
    placeholder_format = "<ID{i}>"

    def __init__(self, max_new_tokens: int = 256, num_beams: int | None = None) -> None:
        self._max_new_tokens = max_new_tokens
        self._num_beams = num_beams or get_settings().INDICTRANS2_NUM_BEAMS
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
            _legacy_cache_adapter(model)
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
            unified = [telugu_to_devanagari(t) if src == "te" else t for t in texts]
            batch_in = [f"{_TAGS[src]} {_TAGS[tgt]} {t}" for t in unified]
        enc = tok(batch_in, truncation=True, padding="longest", return_tensors="pt")
        with torch.inference_mode():
            out = model.generate(
                **enc, max_new_tokens=self._max_new_tokens, num_beams=self._num_beams,
                use_cache=True,
            )
        decoded = tok.batch_decode(out, skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True)
        if ip is not None:
            decoded = ip.postprocess_batch(decoded, lang=_TAGS[tgt])
        elif tgt == "te":
            decoded = [devanagari_to_telugu(d) for d in decoded]
        return decoded

    async def translate(
        self, texts: list[str], source_language: str, target_language: str
    ) -> list[str]:
        if not self.supports(source_language, target_language):
            raise TranslationError(f"unsupported pair {source_language}->{target_language}")
        return await asyncio.to_thread(
            self._translate_sync, texts, source_language, target_language
        )
