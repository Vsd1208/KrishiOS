"""Pydantic v2 schemas for the catalog API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CropOut(BaseModel):
    crop_canonical: str
    name_en: str
    name_te: str
    name_hi: str
    display_name: str
    aliases: list[str]
    crop_group: str
    domain: str
    seasons: list[str]
    yield_unit: str
    tier: str
    vision_supported: bool
    review_status: str


class CropResolveRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^[a-z]{2}$")


class CropMentionOut(BaseModel):
    surface: str
    alias: str
    candidates: list[str]


class CropChoiceOut(BaseModel):
    crop_canonical: str
    display_name: str


class CropResolveResponse(BaseModel):
    status: str
    crop: str | None
    candidates: list[CropChoiceOut]
    mentions: list[CropMentionOut]


class DistrictOut(BaseModel):
    lgd_district_code: int
    district_name: str
    lgd_state_code: int
    state_name: str
    census_2011_code: int | None


class BlockOut(BaseModel):
    lgd_block_code: int
    block_name: str
    lgd_district_code: int
