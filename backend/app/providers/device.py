"""Compute device for local models: ``ML_DEVICE`` = auto | cpu | cuda.

``auto`` uses CUDA when PyTorch sees a GPU (e.g. a Colab benchmark run) and CPU otherwise
(the backend container). Accuracy is device-independent; latency must be reported per device.
"""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings


@lru_cache(maxsize=1)
def resolve_device() -> str:
    wanted = get_settings().ML_DEVICE
    if wanted in {"cpu", "cuda"}:
        return wanted
    try:
        import torch  # noqa: PLC0415

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"
