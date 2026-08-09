"""Tests for Vision authorization and data isolation."""

import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.auth.permissions import Permission
from app.api.dependencies.auth import AuthContext
from app.vision.models.image import CropImage
from app.vision.api.routes import get_analysis


@pytest.mark.asyncio
async def test_farmer_cannot_view_other_farmer_analysis(monkeypatch):
    farmer_a = uuid4()
    farmer_b = uuid4()
    
    # AuthContext for Farmer A
    auth = AuthContext(
        user_uuid=farmer_a,
        role="FARMER",
        permissions=frozenset([Permission.VISION_READ_OWN])
    )
    
    # Mock analysis and image belonging to Farmer B
    class MockAnalysis:
        pass
        
    class MockImage:
        owner_uuid = farmer_b
        
    # Mock session
    class MockSession:
        async def execute(self, stmt):
            class MockResult:
                def first(self):
                    return (MockAnalysis(), MockImage())
            return MockResult()
            
    with pytest.raises(HTTPException) as excinfo:
        await get_analysis(uuid4(), MockSession(), auth)
        
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_officer_can_view_farmer_analysis(monkeypatch):
    officer_id = uuid4()
    farmer_id = uuid4()
    
    # AuthContext for Officer
    auth = AuthContext(
        user_uuid=officer_id,
        role="OFFICER",
        permissions=frozenset([Permission.VISION_READ_OWN, Permission.VISION_READ_FIELD])
    )
    
    class MockAnalysis:
        id = 1
        model_name = "mock"
        status = "COMPLETED"
        __dict__ = {"id": 1, "model_name": "mock", "status": "COMPLETED", "review_status": "AI_SUGGESTED"}
        
    class MockImage:
        uuid = uuid4()
        owner_uuid = farmer_id
        
    class MockSession:
        async def execute(self, stmt):
            class MockResult:
                def first(self):
                    return (MockAnalysis(), MockImage())
            return MockResult()
            
    # Should not raise
    resp = await get_analysis(uuid4(), MockSession(), auth)
    assert resp is not None
