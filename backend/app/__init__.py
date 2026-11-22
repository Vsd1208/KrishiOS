"""KrishiOS backend.

Downloaded models are kept inside the project (``<repo>/models_cache/huggingface``) when that
folder exists, so the whole project can be moved as one folder. An explicit ``HF_HOME`` wins, and
environments without the folder (Docker images, Colab) keep their usual cache.
"""

import os
from pathlib import Path

_MODELS = Path(__file__).resolve().parents[2] / "models_cache" / "huggingface"
if _MODELS.is_dir():
    os.environ.setdefault("HF_HOME", str(_MODELS))
