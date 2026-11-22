"""Access rules for farmer records, staff data and the knowledge base (API auth hardening).

Before this change, farmers, fields, field crops, soil samples, officers, document upload and
the retrieval index build/promote endpoints had no login at all.
"""

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.api.routes import fields as field_routes
from app.auth.permissions import get_permissions_for_role
from app.database.session import get_db_session
from app.main import app
from app.models.user import UserRole
from fastapi.testclient import TestClient

OWN, OTHER = 11, 22


def _field(field_id: int, farmer_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=field_id, field_code=uuid4(), farmer_id=farmer_id,
                           field_name=f"f{field_id}", area=1, soil_type="Loamy", latitude=17,
                           longitude=79, polygon_geojson=None, irrigation_type="Drip",
                           created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")


class _FakeFieldService:
    calls: ClassVar[list] = []

    def __init__(self, _session: object) -> None:
        pass

    async def list_fields(self, *, offset=0, limit=100, farmer_id=None):
        _FakeFieldService.calls.append(farmer_id)
        rows = [_field(1, OWN), _field(2, OTHER)]
        return [r for r in rows if farmer_id is None or r.farmer_id == farmer_id]

    async def get_field(self, field_id: int):
        return _field(field_id, OWN if field_id == 1 else OTHER)


def _login(role: UserRole, linked: int | None = OWN) -> TestClient:
    auth = AuthContext(user_uuid=uuid4(), role=role, permissions=get_permissions_for_role(role),
                       jti=uuid4())
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=linked)  # user.farmer_profile_id
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[field_routes.get_field_service] = lambda: _FakeFieldService(None)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    _FakeFieldService.calls = []
    yield
    app.dependency_overrides.clear()


def test_no_login_is_refused(client: TestClient) -> None:
    for method, path in (("get", "/api/v1/fields"), ("get", "/api/v1/farmers"),
                         ("get", "/api/v1/soil-samples"), ("get", "/api/v1/field-crops"),
                         ("get", "/api/v1/officers"), ("post", "/api/v1/documents/search"),
                         ("post", "/api/v1/indexes/promote"), ("post", "/api/v1/retrieval/search")):
        assert getattr(client, method)(path).status_code == 401, path


def test_farmer_lists_only_own_fields() -> None:
    r = _login(UserRole.FARMER).get("/api/v1/fields")
    assert r.status_code == 200
    assert [f["farmer_id"] for f in r.json()] == [OWN]
    assert _FakeFieldService.calls == [OWN]  # filtered in the query, not after paging


def test_farmer_cannot_open_another_farmers_field() -> None:
    client = _login(UserRole.FARMER)
    assert client.get("/api/v1/fields/1").status_code == 200
    assert client.get("/api/v1/fields/2").status_code == 404  # not 403: no probing


def test_farmer_without_linked_profile_is_refused() -> None:
    assert _login(UserRole.FARMER, linked=None).get("/api/v1/fields").status_code == 403


def test_staff_see_all_fields() -> None:
    r = _login(UserRole.OFFICER, linked=None).get("/api/v1/fields")
    assert r.status_code == 200 and len(r.json()) == 2
    assert _FakeFieldService.calls == [None]


def test_farmer_cannot_change_records_or_the_knowledge_base() -> None:
    client = _login(UserRole.FARMER)
    assert client.delete("/api/v1/fields/1").status_code == 403
    assert client.post("/api/v1/fields", json={}).status_code == 403
    assert client.get("/api/v1/farmers").status_code == 403
    assert client.post("/api/v1/indexes/promote", json={}).status_code == 403
    assert client.post("/api/v1/documents/upload").status_code == 403


def test_officer_cannot_promote_an_index_but_can_read_officers_permission() -> None:
    assert "officer:read" in get_permissions_for_role(UserRole.OFFICER)
    assert "officer:read" not in get_permissions_for_role(UserRole.FARMER)
    assert _login(UserRole.OFFICER).post("/api/v1/indexes/promote",
                                         json={}).status_code == 403
