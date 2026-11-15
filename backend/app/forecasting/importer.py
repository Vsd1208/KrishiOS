"""Import a batch forecast artifact produced by ``ml/scripts/export_yield_forecasts.py``.

Artifact layout (one directory per model version)::

    <YIELD_FORECAST_DIR>/<model_version>/manifest.json
    <YIELD_FORECAST_DIR>/<model_version>/forecasts.jsonl

The manifest names the model, version, generation time, the forecasts file's SHA-256 and row
count, and the validation evidence (run ids). Import is idempotent (same version + hash is a
no-op) and all-or-nothing: one row that breaks the contract rejects the file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.forecasting.schemas import ForecastContractError, YieldForecast, validate
from app.models.forecasting import ForecastImport, YieldForecastRecord

REQUIRED_MANIFEST = ("model_name", "model_version", "generated_at", "file", "sha256", "rows")


@dataclass(frozen=True, slots=True)
class ImportResult:
    model_version: str
    rows: int
    imported: bool
    import_id: int | None
    reason: str = ""


def _parse(row: dict[str, Any]) -> YieldForecast:
    row = dict(row)
    row["generated_at"] = datetime.fromisoformat(row["generated_at"])
    row.pop("change_vs_normal", None)
    return YieldForecast(**row)


def latest_artifact(root: Path) -> Path | None:
    dirs = [d for d in root.glob("*") if (d / "manifest.json").exists()] if root.exists() else []
    if not dirs:
        return None
    return max(dirs, key=lambda d: json.loads((d / "manifest.json").read_text())["generated_at"])


async def import_artifact(session: AsyncSession, directory: Path) -> ImportResult:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_MANIFEST if k not in manifest]
    if missing:
        raise ForecastContractError(f"manifest missing {missing}")
    data = (directory / manifest["file"]).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != manifest["sha256"]:
        raise ForecastContractError("forecasts file does not match the manifest hash")
    version = manifest["model_version"]
    existing = await session.scalar(
        select(ForecastImport).where(ForecastImport.model_version == version,
                                     ForecastImport.file_sha256 == sha))
    if existing is not None:
        return ImportResult(version, existing.rows, False, existing.id, "already imported")
    forecasts = [_parse(json.loads(line)) for line in data.decode("utf-8").splitlines()
                 if line.strip()]
    if len(forecasts) != int(manifest["rows"]):
        raise ForecastContractError("row count does not match the manifest")
    for f in forecasts:
        validate(f)
        if f.model_version != version:
            raise ForecastContractError("row model_version differs from the manifest")
    imp = ForecastImport(model_name=manifest["model_name"], model_version=version,
                         file_sha256=sha, rows=len(forecasts), manifest=manifest,
                         imported_at=datetime.now(UTC))
    session.add(imp)
    await session.flush()
    for f in forecasts:
        d = f.to_dict()
        d.pop("change_vs_normal")
        d.pop("district_id")
        d["generated_at"] = f.generated_at
        session.add(YieldForecastRecord(import_id=imp.id, **d))
    await session.flush()
    return ImportResult(version, len(forecasts), True, imp.id)
