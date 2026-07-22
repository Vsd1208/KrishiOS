"""API tests for Sprint 1 route behavior."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes.farmers import get_farmer_service
from app.main import app


class FakeFarmerService:
    """Small route-level fake for validating API wiring."""

    async def register_farmer(self, payload: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=1,
            farmer_code=UUID("11111111-1111-1111-1111-111111111111"),
            full_name="Ravi Kumar",
            phone="9876543210",
            preferred_language="Hindi",
            district_id=1,
            village="Rampur",
            landholding_acres=Decimal("2.50"),
            created_at=datetime(2026, 7, 22, tzinfo=UTC),
            updated_at=datetime(2026, 7, 22, tzinfo=UTC),
        )


def test_register_farmer_endpoint(client: TestClient) -> None:
    app.dependency_overrides[get_farmer_service] = FakeFarmerService

    response = client.post(
        "/api/v1/farmers",
        json={
            "full_name": "Ravi Kumar",
            "phone": "9876543210",
            "preferred_language": "Hindi",
            "district_id": 1,
            "village": "Rampur",
            "landholding_acres": "2.50",
        },
    )

    assert response.status_code == 201
    assert response.json()["phone"] == "9876543210"

