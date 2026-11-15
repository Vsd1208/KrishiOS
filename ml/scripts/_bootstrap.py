"""Make ``krishios_ml`` (ml/src) and the backend ``app`` package importable.

Evaluation scripts that exercise backend providers run inside the backend venv::

    cd backend
    uv run --extra local-ml --with jiwer --with sacrebleu python ../ml/scripts/<script>.py

They import backend code directly so the evaluated code path is the production one.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ML_ROOT.parent
for p in (ML_ROOT / "src", REPO_ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Backend settings require these; evaluation never touches the database.
os.environ.setdefault("POSTGRES_PASSWORD", "unused-in-evaluation")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUDIO_STORAGE_PATH", str(ML_ROOT / "data" / "interim" / "audio_out"))
