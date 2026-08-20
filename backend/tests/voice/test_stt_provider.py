"""Tests for MockSTTProvider supporting EN, HI, TE, and code-switching."""

import pytest
from pathlib import Path
from app.voice.providers.mock_stt import MockSTTProvider


@pytest.mark.asyncio
async def test_stt_provider_telugu_query():
    provider = MockSTTProvider()
    res = await provider.transcribe(Path("sample_telugu_query.wav"), hint_language="te")

    assert res.detected_language == "te"
    assert "వరి" in res.raw_transcript
    assert res.is_code_switched is False


@pytest.mark.asyncio
async def test_stt_provider_hindi_query():
    provider = MockSTTProvider()
    res = await provider.transcribe(Path("sample_hindi_query.wav"), hint_language="hi")

    assert res.detected_language == "hi"
    assert "धान" in res.raw_transcript


@pytest.mark.asyncio
async def test_stt_provider_code_switched_query():
    provider = MockSTTProvider()
    res = await provider.transcribe(Path("sample_mixed_query.wav"), hint_language="mixed")

    assert res.is_code_switched is True
    assert "crop" in res.raw_transcript


@pytest.mark.asyncio
async def test_stt_provider_low_confidence():
    provider = MockSTTProvider()
    res = await provider.transcribe(Path("sample_low_conf.wav"), hint_language="low_conf")

    assert res.transcription_confidence < 0.5
