"""Tests for MockTTSProvider speech synthesis."""

import pytest
from app.voice.providers.mock_tts import MockTTSProvider


@pytest.mark.asyncio
async def test_tts_provider_synthesis(tmp_path, monkeypatch):
    class MockSettings:
        AUDIO_STORAGE_PATH = str(tmp_path)

    monkeypatch.setattr("app.voice.providers.mock_tts.get_settings", lambda: MockSettings())

    provider = MockTTSProvider()
    res = await provider.synthesize("మీ వరి పైరుకు అగ్గి తెగులు వచ్చింది", language="te")

    assert res.audio_uuid is not None
    assert res.audio_path.exists()
    assert res.language == "te"
    assert res.duration_seconds > 0.0
