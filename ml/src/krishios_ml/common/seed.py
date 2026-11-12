"""Deterministic seeding for experiments."""

from __future__ import annotations

import os
import random

import numpy as np


def seed_everything(seed: int) -> int:
    """Seed Python, NumPy and (if installed) PyTorch. Returns the seed for logging."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:  # torch is an optional, per-phase dependency
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
    return seed
