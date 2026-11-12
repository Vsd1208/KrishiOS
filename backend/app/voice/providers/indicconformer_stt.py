"""AI4Bharat IndicConformer-600M multilingual STT (MIT; gated on Hugging Face).

Runs the published ONNX export through its ``trust_remote_code`` loader on onnxruntime
(CPU), with no NeMo dependency. The model needs the language up front, so the language
comes from:

1. the caller's hint (the farmer's preferred language), else
2. Whisper language ID restricted to en/hi/te (Whisper LID was 60/60 correct on the
   Phase 2 FLEURS sample, run 5c0b02cf7fef). English audio goes to Whisper, since
   IndicConformer covers the 22 scheduled Indian languages and English is not among them.

Decoding: ``rnnt`` (default) or ``ctc`` via ``STT_INDICCONFORMER_DECODING``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Any

from loguru import logger

from app.catalog.text import script_of, tokenize
from app.config.settings import get_settings
from app.providers.hf import ensure_hf_token
from app.voice.providers.stt_base import LanguageDetectionResult, STTResult

MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"
_SCRIPT = {"te": "Telugu", "hi": "Devanagari", "en": "Latin"}
SAMPLE_RATE = 16000


class IndicConformerSTTProvider:
    provider_name = "indicconformer-600m"

    def __init__(self, decoding: str | None = None) -> None:
        s = get_settings()
        self._decoding = decoding or s.STT_INDICCONFORMER_DECODING
        self.model_version = f"600m-multilingual-{self._decoding}"
        self._model: Any = None
        self._lid: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from transformers import AutoModel  # noqa: PLC0415

            ensure_hf_token()
            t0 = perf_counter()
            self._model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True)
            logger.info("IndicConformer loaded | {:.1f}s", perf_counter() - t0)
        return self._model

    def _language_id(self, audio_path: Path) -> tuple[str, float]:
        if self._lid is None:
            from app.voice.providers.whisper_stt import (  # noqa: PLC0415
                FasterWhisperSTTProvider,
            )

            self._lid = FasterWhisperSTTProvider(model_size="small")
        return self._lid._detect_sync(audio_path)

    def _transcribe_sync(self, audio_path: Path, hint: str | None) -> STTResult:
        import torch  # noqa: PLC0415
        from faster_whisper import decode_audio  # noqa: PLC0415

        t0 = perf_counter()
        if hint in {"te", "hi"}:
            lang, lang_conf, lid_ms = hint, 1.0, 0.0
        else:
            lid_t0 = perf_counter()
            lang, lang_conf = self._language_id(audio_path)
            lid_ms = (perf_counter() - lid_t0) * 1000
        if lang == "en":
            return self._lid._transcribe_sync(audio_path, "en")

        audio = decode_audio(str(audio_path), sampling_rate=SAMPLE_RATE)
        wav = torch.from_numpy(audio).float().unsqueeze(0)
        text = str(self._load()(wav, lang, self._decoding)).strip()
        scripts = {script_of(t) for t in tokenize(text)}
        ms = (perf_counter() - t0) * 1000
        duration = len(audio) / SAMPLE_RATE
        return STTResult(
            raw_transcript=text, detected_language=lang,
            language_confidence=round(lang_conf, 3),
            transcription_confidence=0.0,  # the ONNX export exposes no token scores
            model_name=self.provider_name, model_version=self.model_version, inference_ms=ms,
            is_code_switched="latin" in scripts and bool(scripts & {"telugu", "devanagari"}),
            language_detection=LanguageDetectionResult(lang, round(lang_conf, 3),
                                                       _SCRIPT[lang], lid_ms),
            metadata={"audio_duration_s": round(duration, 2),
                      "real_time_factor": round(ms / 1000 / max(duration, 1e-6), 3),
                      "confidence_available": False},
        )

    async def transcribe(self, audio_path: Path, hint_language: str | None = None) -> STTResult:
        return await asyncio.to_thread(self._transcribe_sync, audio_path, hint_language)

    async def detect_language(self, audio_path: Path) -> LanguageDetectionResult:
        lang, conf = await asyncio.to_thread(self._language_id, audio_path)
        return LanguageDetectionResult(lang, round(conf, 3), _SCRIPT[lang])

    async def health(self) -> bool:
        return ensure_hf_token()
