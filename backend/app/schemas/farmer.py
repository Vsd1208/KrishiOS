"""Pydantic schemas for Farmer request and response contracts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import (
    ResponseSchema,
    validate_indian_phone,
    validate_non_negative_decimal,
)


class FarmerCreate(BaseModel):
    """Payload required to register a farmer."""

    full_name: str = Field(min_length=2, max_length=150)
    phone: str
    preferred_language: str = Field(min_length=2, max_length=50)
    district_id: int = Field(gt=0)
    village: str = Field(min_length=2, max_length=150)
    landholding_acres: Decimal

    @field_validator("full_name", "preferred_language", "village")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return validate_indian_phone(value)

    @field_validator("landholding_acres")
    @classmethod
    def validate_landholding(cls, value: Decimal) -> Decimal:
        return validate_non_negative_decimal(value)


class FarmerUpdate(BaseModel):
    """Payload for partial farmer profile updates."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    preferred_language: str | None = Field(default=None, min_length=2, max_length=50)
    district_id: int | None = Field(default=None, gt=0)
    village: str | None = Field(default=None, min_length=2, max_length=150)
    landholding_acres: Decimal | None = None

    @field_validator("full_name", "preferred_language", "village")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

    @field_validator("phone")
    @classmethod
    def validate_optional_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_indian_phone(value)

    @field_validator("landholding_acres")
    @classmethod
    def validate_optional_landholding(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return validate_non_negative_decimal(value)


class FarmerResponse(ResponseSchema, BaseModel):
    """Farmer representation returned by the API."""

    id: int
    farmer_code: UUID
    full_name: str
    phone: str
    preferred_language: str
    district_id: int
    village: str
    landholding_acres: Decimal
    created_at: datetime
    updated_at: datetime
