"""Phase 10d seasonal outlook: export loading, withheld variables, officer-only access."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.auth.permissions import get_permissions_for_role
from app.main import app
from app.models.user import UserRole
from app.seasonal import service
from app.seasonal.service import (
    OutlookUnavailableError,
    latest_export,
    load_export,
    season_view,
)
from fastapi.testclient import TestClient


def _row(code: int, state: str, variable: str) -> dict:
    return {"lgd_district_code": code, "district": f"D{code}", "state": state, "season": "JJAS",
            "variable": variable, "p_below": 0.2, "p_near": 0.3, "p_above": 0.5,
            "lower_tercile": 700.0, "upper_tercile": 850.0}


BODY = {"version": "v2", "generated_at": "2026-11-22T13:00:00+00:00", "data_through": 2024,
        "history": [1951, 2024], "method": "recent normals",
        "seasons": {"JJAS": {"name": "June-September", "issue_month": 6, "variables": {
            "rain": {"unit": "mm", "test_rpss": 0.038, "display": "weak"},
            "tmax": {"unit": "deg C", "test_rpss": 0.19, "display": "show"},
            "tmin": {"unit": "deg C", "test_rpss": 0.01, "display": "withhold"}}}},
        "rows": [_row(509, "Telangana", v) for v in ("rain", "tmax", "tmin")]
        + [_row(1, "Punjab", v) for v in ("rain", "tmax", "tmin")]}


def _export(root: Path, name: str, body: dict, generated: str, tamper: bool = False) -> Path:
    d = root / name
    d.mkdir(parents=True)
    data = json.dumps({**body, "generated_at": generated}).encode()
    (d / "outlook.json").write_bytes(data + (b" " if tamper else b""))
    (d / "manifest.json").write_text(json.dumps({
        "version": name, "generated_at": generated, "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(body["rows"])}))
    return d


def test_newest_export_is_chosen_and_tampering_is_refused(tmp_path: Path) -> None:
    _export(tmp_path, "old", BODY, "2026-01-01T00:00:00+00:00")
    new = _export(tmp_path, "new", BODY, "2026-11-22T00:00:00+00:00")
    assert latest_export(tmp_path) == new and latest_export(tmp_path, "old").name == "old"
    bad = _export(tmp_path, "bad", BODY, "2026-11-23T00:00:00+00:00", tamper=True)
    with pytest.raises(OutlookUnavailableError, match="does not match"):
        load_export(bad)


def test_withheld_variables_have_no_probabilities_and_state_filter() -> None:
    view = season_view(BODY, "JJAS", state="telangana")
    assert [d["lgd_district_code"] for d in view["districts"]] == [509]
    v = view["districts"][0]["variables"]
    assert v["tmin"] is None and v["tmax"]["p_above"] == 0.5
    assert view["variables"]["rain"]["display"] == "weak"


@pytest.fixture
def _reset():
    yield
    app.dependency_overrides.clear()
    service.get_outlook.cache_clear()


def _login(role: UserRole) -> None:
    auth = AuthContext(user_uuid=uuid4(), role=role, permissions=get_permissions_for_role(role),
                       jti=uuid4())
    app.dependency_overrides[get_current_auth_context] = lambda: auth


def test_officers_only(_reset, client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.seasonal.api.get_outlook", lambda: BODY)
    assert client.get("/api/v1/seasonal/outlook").status_code == 401
    _login(UserRole.FARMER)
    assert client.get("/api/v1/seasonal/outlook").status_code == 403
    _login(UserRole.OFFICER)
    r = client.get("/api/v1/seasonal/outlook", params={"season": "JJAS"})
    assert r.status_code == 200 and len(r.json()["districts"]) == 2


def test_missing_export_is_503(_reset, client: TestClient, monkeypatch) -> None:
    def missing():
        raise OutlookUnavailableError("no seasonal outlook has been exported")
    monkeypatch.setattr("app.seasonal.api.get_outlook", missing)
    _login(UserRole.OFFICER)
    r = client.get("/api/v1/seasonal/outlook")
    assert r.status_code == 503
