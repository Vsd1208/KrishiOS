"""Hugging Face access for gated checkpoints.

``pydantic-settings`` reads ``HF_TOKEN`` from ``.env`` but does not export it, while
``huggingface_hub`` reads it from the process environment. Providers call
``ensure_hf_token()`` before loading a gated model.
"""

from __future__ import annotations

import os

from app.config.settings import get_settings


def ensure_hf_token() -> bool:
    """Export ``HF_TOKEN`` to the environment if configured. Returns whether a token exists."""
    token = get_settings().HF_TOKEN
    if token and not os.environ.get("HF_TOKEN"):
        os.environ["HF_TOKEN"] = token
    return bool(os.environ.get("HF_TOKEN"))
