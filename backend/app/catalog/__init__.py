"""Shared crop catalog and LGD geography (Sprint 11).

Every module resolves crops through ``get_crop_catalog()`` and districts through
``get_lgd_directory()``; there are no hard-coded crop strings elsewhere.
"""

from app.catalog.lgd import LGDDirectory, LGDDistrict, get_lgd_directory
from app.catalog.resolver import (
    CropCatalog,
    CropEntry,
    CropMention,
    CropResolution,
    ResolutionStatus,
    get_crop_catalog,
)

__all__ = [
    "CropCatalog",
    "CropEntry",
    "CropMention",
    "CropResolution",
    "LGDDirectory",
    "LGDDistrict",
    "ResolutionStatus",
    "get_crop_catalog",
    "get_lgd_directory",
]
