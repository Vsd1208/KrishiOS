"""Data access repositories for KrishiOS domain models."""

from app.repositories.crop import CropRepository
from app.repositories.district import DistrictRepository
from app.repositories.farmer import FarmerRepository
from app.repositories.field import FieldRepository
from app.repositories.field_crop import FieldCropRepository
from app.repositories.officer import OfficerRepository
from app.repositories.soil_sample import SoilSampleRepository

__all__ = [
    "CropRepository",
    "DistrictRepository",
    "FarmerRepository",
    "FieldCropRepository",
    "FieldRepository",
    "OfficerRepository",
    "SoilSampleRepository",
]

