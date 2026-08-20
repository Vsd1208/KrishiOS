"""Tests for VoiceService pipeline execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.dependencies.auth import AuthContext
from app.auth.permissions import Permission
from app.voice.services.voice_service import VoiceService


@pytest.mark.asyncio
async def test_voice_service_low_confidence_fallback(tmp_path, monkeypatch):
    class MockSettings:
        AUDIO_STORAGE_PATH = str(tmp_path)
        MAX_AUDIO_UPLOAD_SIZE_MB = 25
        MAX_AUDIO_DURATION_SECONDS = 180
        AUDIO_ALLOWED_MIMES = ["audio/wav"]

    monkeypatch.setattr("app.voice.services.validator.get_settings", lambda: MockSettings())
    monkeypatch.setattr("app.voice.services.storage.get_settings", lambda: MockSettings())
    monkeypatch.setattr("app.voice.services.voice_service.get_settings", lambda: MockSettings())

    session = AsyncMock()
    session.add = MagicMock()

    async def _refresh_side_effect(obj):
        if not hasattr(obj, "_uuid_set"):
            obj.id = 1
            obj.uuid = uuid4()
            obj._uuid_set = True

    session.refresh = _refresh_side_effect

    auth = AuthContext(
        user_uuid=uuid4(),
        role="FARMER",
        permissions=frozenset([Permission.VOICE_SUBMIT]),
        jti=uuid4(),
    )

    service = VoiceService(session=session)
    wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00" + b"0" * 1000

    resp = await service.process_voice_query(
        file_bytes=wav_bytes,
        original_filename="sample_low_conf.wav",
        content_type="audio/wav",
        auth=auth,
        hint_language="low_conf",
    )

    assert resp.confidence < 0.5
    assert "clarity was low" in resp.response_text
