"""Local text-to-speech with Meta MMS-TTS (VITS) via transformers.

LICENCE WARNING: the MMS-TTS checkpoints are CC BY-NC 4.0 (non-commercial). They are
suitable for research and the academic demo only. Commercial deployment must switch to a
commercially licensed voice (e.g. AI4Bharat IndicF5 / Indic Parler-TTS once access is
granted, or an approved hosted TTS). The provider info carries this warning.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from loguru import logger

from app.config.settings import get_settings
from app.providers.device import resolve_device
from app.voice.providers.tts_base import TTSResult

_ISO3 = {"te": "tel", "hi": "hin", "en": "eng"}


class MMSTTSProvider:
    provider_name = "mms-tts"
    model_version = "facebook-mms-1b-vits"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._models: dict[str, tuple[Any, Any]] = {}

    def _load(self, language: str) -> tuple[Any, Any]:
        if language not in self._models:
            from transformers import AutoTokenizer, VitsModel  # noqa: PLC0415

            model_id = f"{self._settings.TTS_MMS_MODEL_PREFIX}{_ISO3[language]}"
            tok = AutoTokenizer.from_pretrained(model_id)
            model = VitsModel.from_pretrained(model_id)
            model.eval().to(resolve_device())
            self._models[language] = (tok, model)
            logger.info("MMS-TTS loaded | {}", model_id)
        return self._models[language]

    def _synthesize_sync(self, text: str, language: str) -> TTSResult:
        import numpy as np  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from scipy.io import wavfile  # noqa: PLC0415

        if language not in _ISO3:
            raise ValueError(f"MMS-TTS: unsupported language {language!r}")
        t0 = perf_counter()
        tok, model = self._load(language)
        inputs = tok(text, return_tensors="pt").to(resolve_device())
        with torch.inference_mode():
            wave = model(**inputs).waveform[0].cpu().numpy()
        rate = int(model.config.sampling_rate)
        audio_uuid = uuid4()
        out_dir = Path(self._settings.AUDIO_STORAGE_PATH) / "tts"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{audio_uuid}.wav"
        pcm = np.clip(wave, -1.0, 1.0)
        wavfile.write(out_file, rate, (pcm * 32767).astype(np.int16))
        ms = (perf_counter() - t0) * 1000
        duration = len(wave) / rate
        return TTSResult(
            audio_uuid=audio_uuid, audio_path=out_file, language=language,
            text_length=len(text), duration_seconds=round(duration, 2),
            model_name=self.provider_name, model_version=self.model_version, inference_ms=ms,
            metadata={"sampling_rate": rate, "real_time_factor": round(ms / 1000 / duration, 3),
                      "licence": "CC-BY-NC-4.0"},
        )

    async def synthesize(self, text: str, language: str) -> TTSResult:
        return await asyncio.to_thread(self._synthesize_sync, text, language)

    async def health(self) -> bool:
        return True
