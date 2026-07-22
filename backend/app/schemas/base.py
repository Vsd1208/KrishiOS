"""Reusable Pydantic schema configuration and validation helpers."""

from decimal import Decimal
import re

from pydantic import ConfigDict

INDIAN_PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")


class ResponseSchema:
    """Base mixin enabling Pydantic responses from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


def validate_indian_phone(value: str) -> str:
    """Validate a 10-digit Indian mobile number without country code."""
    normalized = value.strip()
    if not INDIAN_PHONE_PATTERN.fullmatch(normalized):
        msg = "Phone number must be a valid 10-digit Indian mobile number"
        raise ValueError(msg)
    return normalized


def validate_latitude(value: Decimal) -> Decimal:
    """Validate latitude in decimal degrees."""
    if value < Decimal("-90") or value > Decimal("90"):
        msg = "Latitude must be between -90 and 90"
        raise ValueError(msg)
    return value


def validate_longitude(value: Decimal) -> Decimal:
    """Validate longitude in decimal degrees."""
    if value < Decimal("-180") or value > Decimal("180"):
        msg = "Longitude must be between -180 and 180"
        raise ValueError(msg)
    return value


def validate_non_negative_decimal(value: Decimal) -> Decimal:
    """Validate that a decimal value is zero or greater."""
    if value < Decimal("0"):
        msg = "Value must be greater than or equal to zero"
        raise ValueError(msg)
    return value


def validate_positive_decimal(value: Decimal) -> Decimal:
    """Validate that a decimal value is greater than zero."""
    if value <= Decimal("0"):
        msg = "Value must be greater than zero"
        raise ValueError(msg)
    return value


def validate_positive_int(value: int) -> int:
    """Validate that an integer value is greater than zero."""
    if value <= 0:
        msg = "Value must be greater than zero"
        raise ValueError(msg)
    return value
