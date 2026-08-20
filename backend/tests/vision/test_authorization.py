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
        permissions=frozenset([Permission.VISION_READ_OWN]),
        jti=uuid4(),
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
        permissions=frozenset([Permission.VISION_READ_OWN, Permission.VISION_READ_FIELD]),
        jti=uuid4(),
    )
    
    class MockAnalysis:
        id = 1
        uuid = uuid4()
        image_uuid = uuid4()
        model_name = "mock"
        model_version = "0.1.0"
        status = "COMPLETED"
        review_status = "AI_SUGGESTED"
        quality_score = 0.9
        quality_issues = []
        crop_detected = "Paddy"
        observations = []
        candidate_conditions = []
        confidence_score = 0.85
        error_message = None
        started_at = None
        completed_at = None
        
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
