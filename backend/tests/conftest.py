"""Shared pytest configuration for KrishiOS backend tests."""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_NAME", "KrishiOS")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_VERSION", "0.1.0")
# Tests are hermetic: never use live market data or a key from a developer's backend/.env.
os.environ["MARKET_PROVIDER_NAME"] = "mock-market-v1"
os.environ["DATA_GOV_IN_API_KEY"] = ""
# Provider choices in a developer's .env (real vision model, LLM) must not change test results.
os.environ["VISION_PROVIDER"] = "mock-v1"
os.environ["VISION_MODEL_VERSION"] = ""
os.environ["LLM_PROVIDER"] = "local"
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("API_PREFIX", "/api/v1")
os.environ.setdefault("BACKEND_CORS_ORIGINS", '["http://testserver"]')
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "krishios_test")
os.environ.setdefault("POSTGRES_USER", "krishios")
os.environ.setdefault("POSTGRES_PASSWORD", "test-password")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_JSON", "false")

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient]:
    """Provide a FastAPI test client with dependency overrides reset per test."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_session() -> AsyncMock:
    """Provide an async mock shaped like an SQLAlchemy AsyncSession."""
    return AsyncMock()


@pytest.fixture
def officer_client() -> Generator[TestClient]:
    """A test client signed in as an agricultural officer (role permissions, no token needed)."""
    from uuid import uuid4  # noqa: PLC0415

    from app.api.dependencies.auth import AuthContext, get_current_auth_context  # noqa: PLC0415
    from app.auth.permissions import get_permissions_for_role  # noqa: PLC0415
    from app.models.user import UserRole  # noqa: PLC0415

    auth = AuthContext(user_uuid=uuid4(), role=UserRole.OFFICER,
                       permissions=get_permissions_for_role(UserRole.OFFICER), jti=uuid4())
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

