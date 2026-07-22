"""Pydantic schemas for Field request and response contracts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field as PydanticField, field_validator

from app.schemas.base import (
    ResponseSchema,
    validate_latitude,
    validate_longitude,
    validate_positive_decimal,
)


class FieldCreate(BaseModel):
    """Payload required to register a farmer field."""

    farmer_id: int = PydanticField(gt=0)
    field_name: str = PydanticField(min_length=2, max_length=150)
    area: Decimal
    soil_type: str = PydanticField(min_length=2, max_length=100)
    latitude: Decimal
    longitude: Decimal
    polygon_geojson: dict[str, object] | None = None
    irrigation_type: str = PydanticField(min_length=2, max_length=100)

    @field_validator("field_name", "soil_type", "irrigation_type")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("area")
    @classmethod
    def validate_area(cls, value: Decimal) -> Decimal:
        return validate_positive_decimal(value)

    @field_validator("latitude")
    @classmethod
    def validate_latitude_range(cls, value: Decimal) -> Decimal:
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_range(cls, value: Decimal) -> Decimal:
        return validate_longitude(value)


class FieldUpdate(BaseModel):
    """Payload for partial farmer field updates."""

    farmer_id: int | None = PydanticField(default=None, gt=0)
    field_name: str | None = PydanticField(default=None, min_length=2, max_length=150)
    area: Decimal | None = None
    soil_type: str | None = PydanticField(default=None, min_length=2, max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    polygon_geojson: dict[str, object] | None = None
    irrigation_type: str | None = PydanticField(default=None, min_length=2, max_length=100)

    @field_validator("field_name", "soil_type", "irrigation_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

    @field_validator("area")
    @classmethod
    def validate_optional_area(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_positive_decimal(value)

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


class FieldResponse(ResponseSchema, BaseModel):
    """Field representation returned by the API."""

    id: int
    field_code: UUID
    farmer_id: int
    field_name: str
    area: Decimal
    soil_type: str
    latitude: Decimal
    longitude: Decimal
    polygon_geojson: dict[str, object] | None
    irrigation_type: str
    created_at: datetime
    updated_at: datetime
