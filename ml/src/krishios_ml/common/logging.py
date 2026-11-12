"""Loguru configuration shared by ML scripts."""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure a single stderr sink with a compact format."""
    logger.remove()
    logger.add(sys.stderr, level=level, format="{time:HH:mm:ss} | {level:<7} | {message}")
