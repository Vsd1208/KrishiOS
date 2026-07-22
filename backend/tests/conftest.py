"""Shared pytest configuration for KrishiOS backend tests."""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_NAME", "KrishiOS")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_VERSION", "0.1.0")
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
