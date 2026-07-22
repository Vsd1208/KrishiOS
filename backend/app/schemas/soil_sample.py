"""Pydantic schemas for Soil Sample request and response contracts."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.soil_sample import SoilSampleStatus
from app.schemas.base import ResponseSchema, validate_latitude, validate_longitude


class SoilSampleCreate(BaseModel):
    """Payload required to register a soil sample."""

    farmer_id: int = Field(gt=0)
    field_id: int = Field(gt=0)
    collector_id: int = Field(gt=0)
    collection_date: date
    latitude: Decimal
    longitude: Decimal
    status: SoilSampleStatus = SoilSampleStatus.COLLECTED

    @field_validator("latitude")
    @classmethod
    def validate_latitude_range(cls, value: Decimal) -> Decimal:
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_range(cls, value: Decimal) -> Decimal:
        return validate_longitude(value)


class SoilSampleUpdate(BaseModel):
    """Payload for partial soil sample updates."""

    collector_id: int | None = Field(default=None, gt=0)
    collection_date: date | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    status: SoilSampleStatus | None = None

    @field_validator("latitude")
    @classmethod
    def validate_optional_latitude_range(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_optional_longitude_range(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_longitude(value)


class SoilSampleResponse(ResponseSchema, BaseModel):
    """Soil sample representation returned by the API."""

    sample_id: int
    sample_uuid: UUID
    farmer_id: int
    field_id: int
    collector_id: int
    collection_date: date
    latitude: Decimal
    longitude: Decimal
    status: SoilSampleStatus
    created_at: datetime
    updated_at: datetime
