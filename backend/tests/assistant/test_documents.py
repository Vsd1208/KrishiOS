"""Phase 10c document analysis: briefs and summaries, with a check against invented numbers."""

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.agents.providers.llm import LLMResponse
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.assistant.documents import (
    MAX_CHARS,
    DocumentAnalyzer,
    keep_supported_lines,
    split_parts,
)
from app.assistant.wiring import get_document_analyzer
from app.auth.permissions import get_permissions_for_role
from app.main import app
from app.models.user import UserRole
from fastapi.testclient import TestClient

DOC = ("Advisory for Khammam district. Spray imidacloprid 0.3 ml per litre before 15 August "
       "against brown plant hopper in paddy.")


class FakeLLM:
    model_name = "fake"

    def __init__(self, final: str) -> None:
        self.final, self.calls = final, []

    async def generate(self, prompt, system_instruction=None, temperature=0.2, max_tokens=1000):
        self.calls.append(prompt)
        return LLMResponse(content="- notes" if "Key facts" in prompt else self.final,
                           model_name="fake")


class FakeParser:
    def __init__(self, text: str) -> None:
        self.text = text

    async def parse(self, data, filename, mime_type=None):
        return SimpleNamespace(full_text=self.text, total_pages=1), "text/plain"


class FakeExtractor:
    def extract(self, text):
        return SimpleNamespace(to_dict=lambda: {"fields": {"districts": {"value": ["Khammam"]}}})


@dataclass
class Out:
    text: str
    deliverable: bool = True


class FakeTranslator:
    async def translate(self, text, src, tgt, **kw):
        assert kw.get("personal_data") is True
        return Out(f"<{tgt}>{text}")


def test_lines_with_unsupported_numbers_are_dropped() -> None:
    out, dropped = keep_supported_lines("Spray 0.3 ml per litre.\nRepeat after 21 days.", DOC)
    assert out == "Spray 0.3 ml per litre." and dropped == 1


def test_split_parts_respects_size() -> None:
    parts = split_parts(("word " * 300 + "\n\n") * 10, size=2000)
    assert len(parts) > 1 and all(len(p) <= 2100 for p in parts)


async def test_farmer_summary_is_translated_and_checked() -> None:
    llm = FakeLLM("Summary: Spray before 15 August.\nWhat to do:\n- Spray 0.3 ml per litre.\n"
                  "- Use 5 kg urea.")
    a = DocumentAnalyzer(llm, FakeTranslator(), FakeParser(DOC), FakeExtractor())
    out = await a.analyze(b"x", "a.txt", "farmer", "te")
    assert out.dropped_lines == 1 and "5 kg" not in out.text_en
    assert out.text.startswith("<te>") and out.extracted == {}


async def test_officer_brief_has_structured_fields_and_long_documents_are_flagged() -> None:
    a = DocumentAnalyzer(FakeLLM("Document type: advisory"), FakeTranslator(),
                         FakeParser(DOC + "\n\n" + "x " * MAX_CHARS), FakeExtractor())
    out = await a.analyze(b"x", "a.txt", "officer", "en")
    assert out.extracted["fields"]["districts"]["value"] == ["Khammam"]
    assert out.truncated and out.chars_read == MAX_CHARS


async def test_empty_document() -> None:
    llm = FakeLLM("x")
    out = await DocumentAnalyzer(llm, FakeTranslator(), FakeParser("  "), FakeExtractor()
                                 ).analyze(b"", "a.txt")
    assert "No readable text" in out.text and llm.calls == []


@pytest.fixture
def _reset():
    yield
    app.dependency_overrides.clear()


def _login(role: UserRole) -> TestClient:
    auth = AuthContext(user_uuid=uuid4(), role=role, permissions=get_permissions_for_role(role),
                       jti=uuid4())
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_document_analyzer] = lambda: DocumentAnalyzer(
        FakeLLM("Summary: ok"), FakeTranslator(), FakeParser(DOC), FakeExtractor())
    return TestClient(app)


def test_endpoint_rules(_reset, client: TestClient) -> None:
    files = {"file": ("a.txt", b"text", "text/plain")}
    assert client.post("/api/v1/assistant/analyze-document", files=files).status_code == 401
    farmer = _login(UserRole.FARMER)
    r = farmer.post("/api/v1/assistant/analyze-document", files=files,
                    data={"audience": "farmer", "language": "hi"})
    assert r.status_code == 200 and r.json()["text"].startswith("<hi>")
    r = farmer.post("/api/v1/assistant/analyze-document", files=files,
                    data={"audience": "officer"})
    assert r.status_code == 403
    r = _login(UserRole.OFFICER).post("/api/v1/assistant/analyze-document", files=files,
                                      data={"audience": "officer"})
    assert r.status_code == 200 and r.json()["extracted"]["fields"]
