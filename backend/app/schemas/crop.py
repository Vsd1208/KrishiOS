"""Pydantic schemas for Crop request and response contracts."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ResponseSchema, validate_positive_int


class CropCreate(BaseModel):
    """Payload required to create a crop catalog entry."""

    crop_name: str = Field(min_length=2, max_length=150)
    scientific_name: str | None = Field(default=None, min_length=2, max_length=150)
    season: str = Field(min_length=2, max_length=50)
    duration_days: int

    @field_validator("crop_name", "scientific_name", "season")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        return validate_positive_int(value)


class CropUpdate(BaseModel):
    """Payload for partial crop catalog updates."""

    crop_name: str | None = Field(default=None, min_length=2, max_length=150)
    scientific_name: str | None = Field(default=None, min_length=2, max_length=150)
    season: str | None = Field(default=None, min_length=2, max_length=50)
    duration_days: int | None = None

    @field_validator("crop_name", "scientific_name", "season")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

    @field_validator("duration_days")
    @classmethod
    def validate_optional_duration(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return validate_positive_int(value)


class CropResponse(ResponseSchema, BaseModel):
    """Crop catalog representation returned by the API."""

    id: int
    crop_name: str
    scientific_name: str | None
    season: str
    duration_days: int
    created_at: datetime
    updated_at: datetime
