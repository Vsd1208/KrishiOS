"""Pydantic schemas for Officer request and response contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import ResponseSchema, validate_indian_phone


class OfficerCreate(BaseModel):
    """Payload required to register an officer."""

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str
    designation: str = Field(min_length=2, max_length=100)
    district_id: int = Field(gt=0)

    @field_validator("full_name", "designation")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        return validate_indian_phone(value)


class OfficerUpdate(BaseModel):
    """Payload for partial officer profile updates."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = None
    designation: str | None = Field(default=None, min_length=2, max_length=100)
    district_id: int | None = Field(default=None, gt=0)

    @field_validator("full_name", "designation")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.strip().split())

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_optional_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_indian_phone(value)


class OfficerResponse(ResponseSchema, BaseModel):
    """Officer representation returned by the API."""

    id: int
    officer_code: UUID
    full_name: str
    email: EmailStr
    phone: str
    designation: str
    district_id: int
    created_at: datetime
    updated_at: datetime
