"""POST /assistant/ask: needs a login with knowledge:search; returns the service's answer."""

from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.assistant.service import AssistantAnswer
from app.assistant.wiring import get_assistant_service
from app.auth.permissions import get_permissions_for_role
from app.main import app
from app.models.user import UserRole
from fastapi.testclient import TestClient


class _FakeService:
    async def ask(self, question: str, language: str) -> AssistantAnswer:
        return AssistantAnswer(question=question, language=language, answered=True,
                               answer="<te>answer", answer_en="answer [1]",
                               citations=[{"n": 1, "title": "PAU Kharif", "page": 30,
                                           "source_url": None}],
                               model="qwen2.5:7b", timings_ms={"total": 1.0})


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


def _login(role: UserRole) -> TestClient:
    auth = AuthContext(user_uuid=uuid4(), role=role, permissions=get_permissions_for_role(role),
                       jti=uuid4())
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_assistant_service] = _FakeService
    return TestClient(app)


def test_needs_login(client: TestClient) -> None:
    r = client.post("/api/v1/assistant/ask", json={"question": "When to sow?"})
    assert r.status_code == 401


def test_farmer_gets_cited_answer() -> None:
    r = _login(UserRole.FARMER).post("/api/v1/assistant/ask",
                                     json={"question": "యూరియా ఎప్పుడు?", "language": "te"})
    assert r.status_code == 200
    body = r.json()
    assert body["answered"] and body["answer"] == "<te>answer"
    assert body["citations"][0]["page"] == 30


def test_rejects_unsupported_language() -> None:
    r = _login(UserRole.FARMER).post("/api/v1/assistant/ask",
                                     json={"question": "When to sow?", "language": "ta"})
    assert r.status_code == 422
