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
    FarmerContext,
    keep_supported_lines,
    select_parts,
    split_parts,
)
from app.assistant.jobs import JobStore, get_job_store
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
    assert out.truncated and out.parts_read == 5 and out.parts_total > 5


async def test_empty_document() -> None:
    llm = FakeLLM("x")
    out = await DocumentAnalyzer(llm, FakeTranslator(), FakeParser("  "), FakeExtractor()
                                 ).analyze(b"", "a.txt")
    assert "No readable text" in out.text and llm.calls == []


def test_select_parts_keeps_opening_and_relevant_parts() -> None:
    wheat = [f"part {i} about wheat" for i in range(1, 6)]
    parts = ["overview", *wheat, "part 6 about paddy in Khammam", "part 7 about rice"]
    chosen = select_parts(parts, FarmerContext(crops=["paddy"], district="Khammam").terms(),
                          max_parts=3)
    assert chosen == ["overview", "part 6 about paddy in Khammam", "part 7 about rice"]
    assert select_parts(parts, [], max_parts=3) == parts[:3]


async def test_farmer_context_reaches_the_prompt() -> None:
    llm = FakeLLM("Summary: ok")
    await DocumentAnalyzer(llm, FakeTranslator(), FakeParser(DOC), FakeExtractor()).analyze(
        b"x", "a.txt", "farmer", "en", FarmerContext(crops=["paddy"], district="Khammam"))
    assert "This farmer grows paddy in Khammam" in llm.calls[-1]


async def test_jobs_run_one_at_a_time_and_are_private() -> None:
    import asyncio  # noqa: PLC0415

    store = JobStore()
    running: list[int] = []

    async def work(n: int) -> int:
        running.append(n)
        assert len(running) == 1  # never two at once
        await asyncio.sleep(0.01)
        running.pop()
        return n

    a = store.submit("u1", lambda: work(1))
    b = store.submit("u1", lambda: work(2))
    assert store.position(b) == 1
    for _ in range(100):
        if store.get(b.job_id, "u1").status == "done":
            break
        await asyncio.sleep(0.01)
    assert store.get(a.job_id, "u1").result == 1 and store.get(b.job_id, "u1").result == 2
    assert store.get(a.job_id, "someone-else") is None


@pytest.fixture
def _reset():
    yield
    app.dependency_overrides.clear()


def _auth(role: UserRole) -> AuthContext:
    return AuthContext(user_uuid=uuid4(), role=role, permissions=get_permissions_for_role(role),
                       jti=uuid4())


def _poll(client: TestClient, job_id: str) -> dict:
    import time  # noqa: PLC0415

    for _ in range(200):
        body = client.get(f"/api/v1/assistant/analyze-document/{job_id}").json()
        if body.get("status") in ("done", "failed"):
            return body
        time.sleep(0.01)
    return body


def test_endpoint_rules(_reset, client: TestClient) -> None:
    files = {"file": ("a.txt", b"text", "text/plain")}
    assert client.post("/api/v1/assistant/analyze-document", files=files).status_code == 401
    farmer, officer = _auth(UserRole.FARMER), _auth(UserRole.OFFICER)
    store = JobStore()
    app.dependency_overrides[get_job_store] = lambda: store
    app.dependency_overrides[get_document_analyzer] = lambda: DocumentAnalyzer(
        FakeLLM("Summary: ok"), FakeTranslator(), FakeParser(DOC), FakeExtractor())
    with TestClient(app) as c:
        app.dependency_overrides[get_current_auth_context] = lambda: farmer
        r = c.post("/api/v1/assistant/analyze-document", files=files,
                   data={"audience": "farmer", "language": "hi", "crops": "paddy",
                         "district": "Khammam"})
        assert r.status_code == 202
        job_id = r.json()["job_id"]
        body = _poll(c, job_id)
        assert body["status"] == "done" and body["result"]["text"].startswith("<hi>")
        r = c.post("/api/v1/assistant/analyze-document", files=files,
                   data={"audience": "officer"})
        assert r.status_code == 403
        app.dependency_overrides[get_current_auth_context] = lambda: officer
        assert c.get(f"/api/v1/assistant/analyze-document/{job_id}").status_code == 404
        r = c.post("/api/v1/assistant/analyze-document", files=files,
                   data={"audience": "officer"})
        body = _poll(c, r.json()["job_id"])
        assert body["result"]["extracted"]["fields"]
