"""Append-only JSONL experiment log (integrity rule: every metric must be traceable).

Each record stores config, seed, split id, git commit, metrics, wall-clock time and
artifact path. Reports must cite the ``run_id`` of the record they quote.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from krishios_ml.common.paths import EXPERIMENTS_DIR, REPO_ROOT


def current_git_commit(repo_root: Path = REPO_ROOT) -> str:
    """Return the HEAD commit (with ``-dirty`` suffix if the tree has changes).

    Outside a git checkout (e.g. a Colab bundle) the commit recorded at bundle time is read
    from ``KRISHIOS_GIT_COMMIT``.
    """
    import os  # noqa: PLC0415

    if os.environ.get("KRISHIOS_GIT_COMMIT"):
        return os.environ["KRISHIOS_GIT_COMMIT"]
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True
        ).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass(slots=True)
class ExperimentRecord:
    """One experiment run."""

    experiment: str
    config: dict[str, Any]
    seed: int | None
    split_id: str | None
    metrics: dict[str, Any] = field(default_factory=dict)
    artifact_path: str | None = None
    notes: str = ""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    git_commit: str = field(default_factory=current_git_commit)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    wall_clock_s: float | None = None


def append_record(record: ExperimentRecord, log_path: Path | None = None) -> Path:
    """Append a record to ``ml/experiments/<experiment>.jsonl`` and return the path."""
    path = log_path or EXPERIMENTS_DIR / f"{record.experiment}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False, default=str) + "\n")
    return path


@contextmanager
def track_experiment(
    experiment: str,
    config: dict[str, Any],
    seed: int | None = None,
    split_id: str | None = None,
    log_path: Path | None = None,
) -> Iterator[ExperimentRecord]:
    """Context manager that times the block and appends the record on success."""
    record = ExperimentRecord(experiment=experiment, config=config, seed=seed, split_id=split_id)
    t0 = time.perf_counter()
    yield record
    record.wall_clock_s = round(time.perf_counter() - t0, 3)
    append_record(record, log_path)


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read all records from a JSONL log."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
