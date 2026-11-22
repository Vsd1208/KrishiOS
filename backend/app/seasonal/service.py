"""Phase 10d: district seasonal outlook for officers, read from the ML export.

The export (``ml/scripts/export_seasonal_outlook.py``) writes
``<ML_ARTIFACTS_DIR>/seasonal/<version>/{outlook.json, manifest.json}``. The newest version (by
``generated_at``, or ``SEASONAL_OUTLOOK_VERSION`` when set) is loaded once, after checking the
manifest's SHA-256. Each season x variable carries the skill measured on the one-time test
(2006-2024) and a display decision: ``show``, ``weak`` (shown with a weak-signal label) or
``withhold`` (no probabilities are returned; officers are pointed to IMD's official outlook).

A research outlook alongside IMD's official forecasts, not a replacement; anything sent to
farmers goes through officer approval.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SEASONS = ("JJAS", "OND", "JF", "MAM")
VARIABLES = ("rain", "tmax", "tmin")


class OutlookUnavailableError(Exception):
    """No valid export was found."""


def latest_export(root: Path, version: str | None = None) -> Path | None:
    if version:
        d = root / version
        return d if (d / "manifest.json").exists() else None
    dirs = [d for d in root.glob("*") if (d / "manifest.json").exists()] if root.exists() else []
    if not dirs:
        return None
    return max(dirs, key=lambda d: json.loads((d / "manifest.json").read_text(
        encoding="utf-8"))["generated_at"])


def load_export(folder: Path) -> dict[str, Any]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    data = (folder / "outlook.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise OutlookUnavailableError(f"{folder.name}: outlook.json does not match its manifest")
    body = json.loads(data)
    if len(body["rows"]) != int(manifest["rows"]):
        raise OutlookUnavailableError(f"{folder.name}: row count does not match the manifest")
    return body


@lru_cache(maxsize=1)
def get_outlook() -> dict[str, Any]:
    from app.catalog.paths import artifacts_dir  # noqa: PLC0415
    from app.config.settings import get_settings  # noqa: PLC0415

    folder = latest_export(artifacts_dir() / "seasonal", get_settings().SEASONAL_OUTLOOK_VERSION)
    if folder is None:
        raise OutlookUnavailableError("no seasonal outlook has been exported")
    return load_export(folder)


def season_view(body: dict[str, Any], season: str, state: str | None = None,
                district_code: int | None = None) -> dict[str, Any]:
    """One season: its variables' skill and display, and district rows (withheld variables have
    no probabilities)."""
    meta = body["seasons"][season]
    display = {v: meta["variables"][v]["display"] for v in VARIABLES}
    districts: dict[int, dict[str, Any]] = {}
    for r in body["rows"]:
        if r["season"] != season:
            continue
        if district_code is not None and r["lgd_district_code"] != district_code:
            continue
        if state and (r.get("state") or "").casefold() != state.casefold():
            continue
        d = districts.setdefault(r["lgd_district_code"], {
            "lgd_district_code": r["lgd_district_code"], "district": r["district"],
            "state": r.get("state"), "variables": {}})
        if display[r["variable"]] == "withhold":
            d["variables"][r["variable"]] = None
        else:
            d["variables"][r["variable"]] = {
                k: r[k] for k in ("p_below", "p_near", "p_above", "lower_tercile",
                                  "upper_tercile")}
    return {"version": body["version"], "season": season, "season_name": meta["name"],
            "issue_month": meta["issue_month"], "data_through": body["data_through"],
            "history": body["history"], "method": body["method"],
            "variables": meta["variables"],
            "districts": sorted(districts.values(), key=lambda d: (d["state"] or "",
                                                                   d["district"]))}
