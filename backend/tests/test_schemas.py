"""Unit tests for Sprint 1 Pydantic schema validation."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.field_crop import FieldCropStatus
from app.schemas.farmer import FarmerCreate
from app.schemas.field import FieldCreate
from app.schemas.field_crop import FieldCropCreate


def test_farmer_create_validates_indian_phone() -> None:
    with pytest.raises(ValidationError):
        FarmerCreate(
            full_name="Ravi Kumar",
            phone="1234567890",
            preferred_language="Hindi",
            district_id=1,
            village="Rampur",
            landholding_acres=Decimal("2.50"),
        )


def test_field_create_validates_coordinate_ranges() -> None:
    with pytest.raises(ValidationError):
        FieldCreate(
            farmer_id=1,
            field_name="North Plot",
            area=Decimal("1.25"),
            soil_type="Loamy",
            latitude=Decimal("91"),
            longitude=Decimal("77.123456"),
            irrigation_type="Drip",
        )


def test_field_crop_create_validates_harvest_after_sowing() -> None:
    with pytest.raises(ValidationError):
        FieldCropCreate(
            field_id=1,
            crop_id=1,
            sowing_date=date(2026, 7, 1),
            harvesting_date=date(2026, 6, 1),
            status=FieldCropStatus.SOWN,
        )

