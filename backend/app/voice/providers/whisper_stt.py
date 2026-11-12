"""Local speech-to-text with faster-whisper (CTranslate2). MIT licence, CPU-friendly (int8).

Language identification is restricted to ``SUPPORTED_LANGUAGES`` (en/hi/te): Whisper's own
LID probabilities are renormalised over those languages, so a Telugu speaker is never
transcribed as Kannada or Tamil. Code-switching is flagged when the transcript mixes Latin
with Telugu or Devanagari script. Requires the ``local-ml`` extra.
"""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from time import perf_counter
from typing import Any

from loguru import logger

from app.catalog.text import script_of, tokenize
from app.config.settings import get_settings
from app.voice.providers.stt_base import LanguageDetectionResult, STTResult

_SCRIPT = {"te": "Telugu", "hi": "Devanagari", "en": "Latin"}


class FasterWhisperSTTProvider:
    """Whisper on CPU via faster-whisper."""

    def __init__(self, model_size: str | None = None, compute_type: str | None = None) -> None:
        s = get_settings()
        self._size = model_size or s.STT_WHISPER_MODEL
        self._compute = compute_type or s.STT_WHISPER_COMPUTE_TYPE
        self._beam = s.STT_WHISPER_BEAM_SIZE
        self._temperature = (
            [0.0, 0.2, 0.4, 0.6, 0.8, 1.0] if s.STT_WHISPER_TEMPERATURE_FALLBACK else 0.0
        )
        self._languages = [lang for lang in s.SUPPORTED_LANGUAGES if lang in _SCRIPT]
        self._model: Any = None

    @property
    def provider_name(self) -> str:
        return f"faster-whisper-{self._size}"

    @property
    def model_version(self) -> str:
        return f"{self._size}-{self._compute}"

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel  # noqa: PLC0415 - optional extra

            t0 = perf_counter()
            self._model = WhisperModel(self._size, device="cpu", compute_type=self._compute)
            logger.info("faster-whisper loaded | size={} | {:.1f}s", self._size,
                        perf_counter() - t0)
        return self._model

    def _detect_sync(self, audio_path: Path) -> tuple[str, float]:
        from faster_whisper import decode_audio  # noqa: PLC0415

        model = self._load()
        audio = decode_audio(str(audio_path), sampling_rate=16000)
        _, _, all_probs = model.detect_language(audio)
        probs = {lang: p for lang, p in all_probs if lang in self._languages}
        total = sum(probs.values()) or 1.0
        lang = max(probs, key=probs.__getitem__) if probs else "en"
        return lang, probs.get(lang, 0.0) / total

    def _transcribe_sync(self, audio_path: Path, hint: str | None) -> STTResult:
        t0 = perf_counter()
        lid_t0 = perf_counter()
        if hint in self._languages:
            lang, lang_conf = hint, 1.0
        else:
            lang, lang_conf = self._detect_sync(audio_path)
        lid_ms = (perf_counter() - lid_t0) * 1000
        segments, info = self._load().transcribe(
            str(audio_path), language=lang, beam_size=self._beam, vad_filter=True,
            temperature=self._temperature, condition_on_previous_text=False,
        )
        segs = list(segments)
        text = " ".join(seg.text.strip() for seg in segs).strip()
        # Mean per-token probability as a transcription-confidence proxy.
        logprobs = [seg.avg_logprob for seg in segs if seg.avg_logprob is not None]
        confidence = math.exp(sum(logprobs) / len(logprobs)) if logprobs else 0.0
        scripts = {script_of(t) for t in tokenize(text)}
        code_switched = "latin" in scripts and bool(scripts & {"telugu", "devanagari"})
        ms = (perf_counter() - t0) * 1000
        return STTResult(
            raw_transcript=text,
            detected_language=lang,
            language_confidence=round(lang_conf, 3),
            transcription_confidence=round(confidence, 3),
            model_name=self.provider_name,
            model_version=self.model_version,
            inference_ms=ms,
            is_code_switched=code_switched,
            language_detection=LanguageDetectionResult(lang, round(lang_conf, 3), _SCRIPT[lang],
                                                       lid_ms),
            metadata={"audio_duration_s": round(info.duration, 2),
                      "real_time_factor": round(ms / 1000 / max(info.duration, 1e-6), 3)},
        )

    async def transcribe(self, audio_path: Path, hint_language: str | None = None) -> STTResult:
        return await asyncio.to_thread(self._transcribe_sync, audio_path, hint_language)

    async def detect_language(self, audio_path: Path) -> LanguageDetectionResult:
        lang, conf = await asyncio.to_thread(self._detect_sync, audio_path)
        return LanguageDetectionResult(lang, round(conf, 3), _SCRIPT[lang])

    async def health(self) -> bool:
        try:
            import faster_whisper  # noqa: F401, PLC0415
        except ImportError:
            return False
        return True
