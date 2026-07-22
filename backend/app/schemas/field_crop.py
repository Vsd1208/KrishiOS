"""Pydantic schemas for field crop assignment and history contracts."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.field_crop import FieldCropStatus
from app.schemas.base import ResponseSchema


class FieldCropCreate(BaseModel):
    """Payload required to assign a crop to a field."""

    field_id: int = Field(gt=0)
    crop_id: int = Field(gt=0)
    sowing_date: date
    harvesting_date: date | None = None
    status: FieldCropStatus = FieldCropStatus.PLANNED

    @model_validator(mode="after")
    def validate_harvesting_date(self) -> "FieldCropCreate":
        if self.harvesting_date is not None and self.harvesting_date < self.sowing_date:
            msg = "Harvesting date must be on or after sowing date"
            raise ValueError(msg)
        return self


class FieldCropUpdate(BaseModel):
    """Payload for partial field crop history updates."""

    crop_id: int | None = Field(default=None, gt=0)
    sowing_date: date | None = None
    harvesting_date: date | None = None
    status: FieldCropStatus | None = None

    @model_validator(mode="after")
    def validate_optional_harvesting_date(self) -> "FieldCropUpdate":
        if (
            self.sowing_date is not None
            and self.harvesting_date is not None
            and self.harvesting_date < self.sowing_date
        ):
            msg = "Harvesting date must be on or after sowing date"
            raise ValueError(msg)
        return self


class FieldCropResponse(ResponseSchema, BaseModel):
    """Field crop history representation returned by the API."""

    id: int
    field_id: int
    crop_id: int
    sowing_date: date
    harvesting_date: date | None
    status: FieldCropStatus
    created_at: datetime
    updated_at: datetime
