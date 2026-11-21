"""KrishiOS ML: research, training and evaluation code (separate from the backend).

Downloaded models are kept inside the project (``<repo>/models_cache/huggingface``) when that
folder exists, so the whole project can be moved as one folder. An explicit ``HF_HOME`` wins.
"""

import os
from pathlib import Path

__version__ = "0.1.0"

_MODELS = Path(__file__).resolve().parents[3] / "models_cache" / "huggingface"
if _MODELS.is_dir():
    os.environ.setdefault("HF_HOME", str(_MODELS))
