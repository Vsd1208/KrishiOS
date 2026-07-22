"""Unit tests for Sprint 1 service-layer business rules."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.exceptions.domain import EntityConflictError, EntityValidationError
from app.schemas.farmer import FarmerCreate
from app.schemas.soil_sample import SoilSampleCreate
from app.services.farmer import FarmerService
from app.services.soil_sample import SoilSampleService


@pytest.mark.asyncio
async def test_farmer_service_rejects_duplicate_phone(mock_session: AsyncMock) -> None:
    service = FarmerService(mock_session)
    service.districts = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=1)))
    service.farmers = SimpleNamespace(get_by_phone=AsyncMock(return_value=SimpleNamespace(id=9)))

    payload = FarmerCreate(
        full_name="Ravi Kumar",
        phone="9876543210",
        preferred_language="Hindi",
        district_id=1,
        village="Rampur",
        landholding_acres=Decimal("2.5"),
    )

    with pytest.raises(EntityConflictError):
        await service.register_farmer(payload)


@pytest.mark.asyncio
async def test_soil_sample_service_requires_field_to_belong_to_farmer(mock_session: AsyncMock) -> None:
    service = SoilSampleService(mock_session)
    service.farmers = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=1)))
    service.fields = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=2, farmer_id=99)))
    service.officers = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=3)))

    payload = SoilSampleCreate(
        farmer_id=1,
        field_id=2,
        collector_id=3,
        collection_date="2026-07-22",
        latitude=Decimal("28.613900"),
        longitude=Decimal("77.209000"),
    )

    with pytest.raises(EntityValidationError):
        await service.register_soil_sample(payload)
