"""Import-order regression: entry points that import the catalog ORM first must work."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def test_catalog_models_importable_first() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import app.catalog.models; import scripts.seed_reference_data"],
        cwd=BACKEND, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
