"""Canonical filesystem locations inside ``ml/``."""

from __future__ import annotations

from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ML_ROOT.parent
REFERENCE_DIR = ML_ROOT / "reference"
DATA_DIR = ML_ROOT / "data"
ARTIFACTS_DIR = ML_ROOT / "artifacts"
EXPERIMENTS_DIR = ML_ROOT / "experiments"
REPORTS_DIR = ML_ROOT / "reports"
