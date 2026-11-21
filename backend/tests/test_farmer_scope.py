"""A farmer login is scoped to its own farmer profile, looked up from ``user.farmer_profile_id``.

The access token holds only the user's UUID, role and permissions. Before the UI polish the alert,
decision and preference routes read a ``farmer_profile_id`` attribute the auth context never had,
so every farmer request to them failed with a server error, and the frontend had no way to load
the signed-in farmer's own profile.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context, linked_farmer_id
from app.api.routes import farmers as farmer_routes
from app.database.session import get_db_session
from app.main import app
from app.models.user import UserRole
from app.proactive.api import routes as proactive_routes
from fastapi.testclient import TestClient


def _auth(role: UserRole = UserRole.FARMER) -> AuthContext:
    return AuthContext(user_uuid=uuid4(), role=role, permissions=frozenset(), jti=uuid4())


def _session(linked: int | None) -> AsyncMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=linked)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_linked_farmer_id_reads_the_user_row() -> None:
    session = _session(42)
    assert await linked_farmer_id(session, _auth()) == 42
    session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_farmer_alerts_are_filtered_to_the_linked_farmer() -> None:
    session = _session(7)
    out = await proactive_routes.list_alerts(
        farmer_id=None, status_filter=None, limit=50, offset=0, session=session, auth=_auth()
    )
    assert out == []
    stmt = session.execute.await_args.args[0]
    assert "farmer_id" in str(stmt)
    assert stmt.compile().params.get("farmer_id_1") == 7


@pytest.mark.asyncio
async def test_farmer_without_a_profile_gets_no_alerts_or_decisions() -> None:
    session = _session(None)
    assert await proactive_routes.list_alerts(
        farmer_id=None, status_filter=None, limit=50, offset=0, session=session, auth=_auth()
    ) == []
    assert await proactive_routes.list_decisions(
        farmer_id=None, limit=50, offset=0, session=session, auth=_auth()
    ) == []
    session.execute.assert_not_awaited()


class _FakeService:
    def __init__(self, _session: object) -> None:
        pass

    async def get_farmer(self, farmer_id: int) -> dict:
        now = datetime(2026, 11, 20, tzinfo=UTC)
        return {
            "id": farmer_id, "farmer_code": uuid4(), "full_name": "Ravi Kumar",
            "phone": "9876543210", "preferred_language": "te", "district_id": 1,
            "village": "Rampur", "landholding_acres": Decimal("2.50"),
            "created_at": now, "updated_at": now,
        }


def _client(monkeypatch: pytest.MonkeyPatch, linked: int | None) -> TestClient:
    monkeypatch.setattr(farmer_routes, "FarmerService", _FakeService)
    app.dependency_overrides[get_current_auth_context] = _auth
    app.dependency_overrides[get_db_session] = lambda: _session(linked)
    return TestClient(app)


def test_me_returns_the_signed_in_farmer(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = _client(monkeypatch, 11).get("/api/v1/farmers/me")
    assert response.status_code == 200
    assert response.json()["id"] == 11


def test_me_is_404_without_a_linked_profile(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _client(monkeypatch, None).get("/api/v1/farmers/me").status_code == 404


def test_me_needs_a_login(client: TestClient) -> None:
    assert client.get("/api/v1/farmers/me").status_code == 401
