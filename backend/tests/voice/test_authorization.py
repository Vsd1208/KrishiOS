"""Tests for Voice authorization and ownership isolation."""

import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.api.dependencies.auth import AuthContext
from app.auth.permissions import Permission
from app.voice.api.routes import get_audio_record, delete_audio_record


@pytest.mark.asyncio
async def test_farmer_cannot_access_other_farmer_audio():
    user_a = uuid4()
    user_b = uuid4()

    auth = AuthContext(
        user_uuid=user_a,
        role="FARMER",
        permissions=frozenset([Permission.VOICE_READ_OWN]),
        jti=uuid4(),
    )

    class MockAudioRecord:
        owner_uuid = user_b

    class MockSession:
        async def execute(self, stmt):
            class MockResult:
                def scalar_one_or_none(self):
                    return MockAudioRecord()
            return MockResult()

    with pytest.raises(HTTPException) as excinfo:
        await get_audio_record(uuid4(), MockSession(), auth)

    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_farmer_cannot_delete_other_farmer_audio():
    user_a = uuid4()
    user_b = uuid4()

    auth = AuthContext(
        user_uuid=user_a,
        role="FARMER",
        permissions=frozenset([Permission.VOICE_DELETE]),
        jti=uuid4(),
    )

    class MockAudioRecord:
        owner_uuid = user_b

    class MockSession:
        async def execute(self, stmt):
            class MockResult:
                def scalar_one_or_none(self):
                    return MockAudioRecord()
            return MockResult()

    with pytest.raises(HTTPException) as excinfo:
        await delete_audio_record(uuid4(), MockSession(), auth)

    assert excinfo.value.status_code == 403
