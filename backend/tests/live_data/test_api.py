"""Tests for Live Data API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from unittest.mock import AsyncMock
from uuid import uuid4

from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.main import app


@pytest.mark.asyncio
async def test_api_get_current_weather():
    mock_auth = AuthContext(
        user_uuid=uuid4(),
        role="FARMER",
        permissions=frozenset([Permission.WEATHER_READ, Permission.LIVE_DATA_READ]),
        jti=uuid4(),
    )

    mock_db = AsyncMock()

    app.dependency_overrides[get_current_auth_context] = lambda: mock_auth
    app.dependency_overrides[get_db_session] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/live/weather/current?district=Warangal&state=Telangana")
        assert resp.status_code == 200
        data = resp.json()
        assert data["temperature_celsius"] > 0
        assert data["freshness"] == "FRESH"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_get_market_prices():
    mock_auth = AuthContext(
        user_uuid=uuid4(),
        role="FARMER",
        permissions=frozenset([Permission.MARKET_READ, Permission.LIVE_DATA_READ]),
        jti=uuid4(),
    )

    mock_db = AsyncMock()

    app.dependency_overrides[get_current_auth_context] = lambda: mock_auth
    app.dependency_overrides[get_db_session] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/live/market/prices?commodity=Paddy&district=Warangal&state=Telangana")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert data[0]["commodity"] == "Paddy"

    app.dependency_overrides.clear()
