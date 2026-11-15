"""Phase 8 flows against a real Postgres (see test_phase3_db.py for the setup): forecast import
(idempotent), shortfall -> officer-review draft, outlook / forecast API, insurance helper."""

import hashlib
import json
import os
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("KRISHIOS_INTEGRATION_DB") != "1",
                                reason="needs a migrated Postgres (KRISHIOS_INTEGRATION_DB=1)")


def _rows(version: str) -> list[dict]:
    gen = datetime.now(UTC).isoformat()
    base = {"lgd_district_code": 509, "season": "Rabi", "crop_year": 2026, "forecast_lead": 30,
            "unit": "Tonnes/Hectare", "model_name": "b3-test", "model_version": version,
            "generated_at": gen, "available_modalities": ["weather", "yield_history"],
            "missing_modalities": [], "district_id": None, "in_distribution": True}
    return [
        {**base, "crop_canonical": "groundnut", "crop_tier": "A", "predicted_yield": 1.0,
         "interval_low": 0.6, "interval_high": 1.4, "normal_yield": 2.0,
         "requires_human_review": False, "abstained": False, "abstain_reason": None},
        {**base, "crop_canonical": "paddy", "crop_tier": "A", "predicted_yield": 3.4,
         "interval_low": 2.0, "interval_high": 4.8, "normal_yield": 3.5,
         "requires_human_review": False, "abstained": False, "abstain_reason": None},
        {**base, "crop_canonical": "ragi", "crop_tier": "C", "predicted_yield": None,
         "interval_low": None, "interval_high": None, "normal_yield": None,
         "requires_human_review": False, "abstained": True,
         "abstain_reason": "insufficient data (tier C)"},
    ]


def _artifact(root, version: str):
    d = root / "forecasts" / version
    d.mkdir(parents=True)
    data = "\n".join(json.dumps(r) for r in _rows(version)).encode()
    (d / "forecasts.jsonl").write_bytes(data)
    (d / "manifest.json").write_text(json.dumps({
        "model_name": "b3-test", "model_version": version,
        "generated_at": datetime.now(UTC).isoformat(), "file": "forecasts.jsonl",
        "sha256": hashlib.sha256(data).hexdigest(), "rows": 3}))


def test_import_shortfall_draft_outlook_and_insurance(client, tmp_path, monkeypatch) -> None:
    from app.api.dependencies.auth import get_current_auth_context  # noqa: PLC0415
    from app.catalog import paths  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415
    from app.models.user import UserRole  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    from tests.integration.test_phase4_db import _engine, as_role  # noqa: PLC0415

    version = f"b3-test-{datetime.now(UTC).timestamp():.0f}"
    _artifact(tmp_path, version)
    monkeypatch.setattr(paths, "artifacts_dir", lambda: tmp_path)

    app.dependency_overrides[get_current_auth_context] = lambda: as_role(UserRole.OFFICER)
    first = client.post("/api/v1/forecasting/import").json()
    assert first["imported"] is True and first["rows"] == 3
    assert first["shortfalls"] == 1 and first["drafts"] == 1
    again = client.post("/api/v1/forecasting/import").json()
    assert again["imported"] is False and again["reason"] == "already imported"

    with _engine().begin() as c:
        row = c.execute(text(
            "SELECT status, source_type, severity, district_codes, title FROM govt_bulletin "
            "WHERE source_name = :k"), {"k": f"yield:{version}:509:Rabi:2026"}).one()
    assert row.status == "needs_review" and row.source_type == "forecast"
    assert row.severity == "MEDIUM" and row.district_codes == [509]

    out = client.get("/api/v1/forecasting/outlook?lgd_district_code=509&season=Rabi").json()
    assert out["counts"] == {"forecasts": 2, "abstained": 1, "likely_shortfall": 1,
                             "needs_review": 0}
    gn = next(i for i in out["items"] if i["crop_canonical"] == "groundnut")
    assert gn["likely_shortfall"] and gn["official"] is False and gn["crop_names"]["te"]

    app.dependency_overrides[get_current_auth_context] = lambda: as_role(UserRole.FARMER)
    f = client.get("/api/v1/forecasting/forecast?lgd_district_code=509&crop=rice").json()
    assert f["forecast"]["crop_canonical"] == "paddy" and f["status"] == "ok"
    denied = client.get("/api/v1/forecasting/outlook?lgd_district_code=509")
    assert denied.status_code == 403  # the district outlook is for officers
    ins = client.get("/api/v1/schemes/insurance/helper?lgd_district_code=509&crop=groundnut"
                     "&season=Rabi&language=te").json()
    ctx = ins["yield_context"]
    assert ctx["official"] is False and "YES-TECH" in ctx["notice"]
    if ins["status"] != "verified":
        assert ins["guidance"] == []  # unverified guidance is never shown to farmers
    app.dependency_overrides.clear()
