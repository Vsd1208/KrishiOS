"""Regression tests for Sprint 11 voice fixes."""

from pathlib import Path

from app.voice.providers.mock_stt import MockSTTProvider, _filename_tokens

VOICE_SERVICE = Path(__file__).resolve().parents[2] / "app/voice/services/voice_service.py"


def test_filename_tokens() -> None:
    assert _filename_tokens(Path("query_te.wav")) == {"query", "te"}


async def test_test_wav_is_not_telugu() -> None:
    det = await MockSTTProvider().detect_language(Path("test.wav"))
    assert det.language_code == "en"


async def test_explicit_te_token_is_telugu() -> None:
    det = await MockSTTProvider().detect_language(Path("farmer-te-01.wav"))
    assert det.language_code == "te"


def test_voice_service_has_no_paddy_default_or_hardcoded_mock_llm() -> None:
    src = VOICE_SERVICE.read_text(encoding="utf-8")
    assert '"Paddy"' not in src
    assert "MockLocalLLMProvider()" not in src
