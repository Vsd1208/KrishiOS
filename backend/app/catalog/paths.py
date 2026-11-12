"""Location of the committed reference tables (``ml/reference``)."""

from __future__ import annotations

from pathlib import Path

from app.config.settings import get_settings


def reference_dir() -> Path:
    """``REFERENCE_DATA_DIR`` if set, else ``<repo>/ml/reference`` (local development)."""
    configured = get_settings().REFERENCE_DATA_DIR
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "ml" / "reference"
