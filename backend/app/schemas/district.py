"""Pydantic schemas for District request and response contracts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ResponseSchema, validate_latitude, validate_longitude


class DistrictCreate(BaseModel):
    """Payload required to create a district."""

    state: str = Field(min_length=2, max_length=100)
    district_name: str = Field(min_length=2, max_length=150)
    latitude: Decimal
    longitude: Decimal

    @field_validator("state", "district_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("latitude")
    @classmethod
    def validate_latitude_range(cls, value: Decimal) -> Decimal:
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_range(cls, value: Decimal) -> Decimal:
        return validate_longitude(value)


class DistrictUpdate(BaseModel):
    """Payload for partial district updates."""

    state: str | None = Field(default=None, min_length=2, max_length=100)
    district_name: str | None = Field(default=None, min_length=2, max_length=150)
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    @field_validator("state", "district_name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

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


class DistrictResponse(ResponseSchema, BaseModel):
    """District representation returned by the API."""

    id: int
    state: str
    district_name: str
    latitude: Decimal
    longitude: Decimal
    created_at: datetime
    updated_at: datetime
