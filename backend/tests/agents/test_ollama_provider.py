"""Phase 10c: the on-device Ollama LLM provider."""

import json

import httpx
import pytest
from app.agents.providers.llm import OllamaLLMProvider
from app.config.settings import get_settings
from app.providers import ProviderKind
from app.providers.status import _llm_info


def _transport(seen: list) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={
            "message": {"role": "assistant", "content": "Spray in the evening."},
            "prompt_eval_count": 40, "eval_count": 6, "done_reason": "stop",
            "total_duration": 1_500_000_000,
        })
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_generate_sends_chat_and_reads_reply() -> None:
    seen: list = []
    llm = OllamaLLMProvider("http://127.0.0.1:11435", "qwen2.5:3b", transport=_transport(seen))
    out = await llm.generate("When to spray?", system_instruction="Be brief.", temperature=0.1,
                             max_tokens=50)
    assert out.content == "Spray in the evening."
    assert (out.prompt_tokens, out.completion_tokens, out.total_tokens) == (40, 6, 46)
    assert out.metadata["total_duration_ms"] == 1500
    body = seen[0]
    assert body["model"] == "qwen2.5:3b" and body["stream"] is False
    assert body["messages"][0] == {"role": "system", "content": "Be brief."}
    assert body["options"] == {"temperature": 0.1, "num_predict": 50}


@pytest.mark.parametrize("url", ["http://example.com:11434", "https://10.0.0.5:11434"])
def test_remote_server_is_refused(url: str) -> None:
    with pytest.raises(ValueError, match="must point to this machine"):
        OllamaLLMProvider(url, "qwen2.5:3b")


@pytest.mark.parametrize("url", ["http://localhost:11434", "http://host.docker.internal:11435",
                                 "http://ollama:11434"])
def test_local_servers_are_allowed(url: str) -> None:
    assert OllamaLLMProvider(url, "qwen2.5:3b").provider_name == "ollama"


def test_status_reports_ollama_as_live_and_on_device() -> None:
    settings = get_settings().model_copy(update={"LLM_PROVIDER": "ollama",
                                                 "OLLAMA_MODEL": "qwen2.5:3b"})
    info = _llm_info(settings).info
    assert info.kind is ProviderKind.LIVE and info.name == "ollama"
    assert info.version == "qwen2.5:3b" and not info.sends_data_off_device
