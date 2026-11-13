"""Optional model preload at startup (PRELOAD_MODELS=true).

Local models (IndicTrans2, IndicConformer/Whisper, MMS-TTS) load lazily on first use, which made
the first farmer request wait ~78 s on CPU. When enabled, the configured providers that expose
``warm_up()`` are loaded in a background thread after startup, so the API is up immediately and
a failure only logs a warning (the provider still loads lazily, or fails loudly, on first use).
"""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from loguru import logger

from app.config.settings import Settings


def _configured(settings: Settings) -> list[tuple[str, str, Any]]:
    from app.translation.selection import translation_selector  # noqa: PLC0415
    from app.voice.providers.selection import stt_selector, tts_selector  # noqa: PLC0415

    wanted = [
        ("translation", settings.TRANSLATION_PROVIDER, translation_selector),
        ("translation", settings.TRANSLATION_FALLBACK_PROVIDER, translation_selector),
        ("stt", settings.STT_PROVIDER, stt_selector),
        ("tts", settings.TTS_PROVIDER, tts_selector),
    ]
    seen: set[tuple[str, str]] = set()
    out = []
    for capability, name, selector in wanted:
        if name and (capability, name) not in seen:
            seen.add((capability, name))
            out.append((capability, name, selector))
    return out


def warm_up_models(settings: Settings) -> dict[str, str]:
    """Load every configured provider that has ``warm_up``; returns name -> outcome."""
    outcomes: dict[str, str] = {}
    for capability, name, selector in _configured(settings):
        key = f"{capability}:{name}"
        try:
            provider = selector.get(name)
        except Exception as exc:  # preload must never break startup
            outcomes[key] = f"skipped ({type(exc).__name__})"
            continue
        warm_up = getattr(provider, "warm_up", None)
        if warm_up is None:
            outcomes[key] = "no local model"
            continue
        t0 = perf_counter()
        try:
            warm_up()
            outcomes[key] = f"loaded in {perf_counter() - t0:.1f}s"
        except Exception as exc:
            outcomes[key] = f"failed ({type(exc).__name__}: {exc})"
            logger.warning("Model preload failed | {} | {}", key, exc)
    logger.info("Model preload finished | {}", outcomes)
    return outcomes


def start_preload(settings: Settings) -> asyncio.Task[dict[str, str]] | None:
    if not settings.PRELOAD_MODELS:
        return None
    logger.info("Preloading local models in the background")
    return asyncio.create_task(asyncio.to_thread(warm_up_models, settings))
