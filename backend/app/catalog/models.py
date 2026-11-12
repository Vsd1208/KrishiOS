"""Re-export of the catalog ORM model (defined with the domain models to avoid cycles)."""

from app.models.crop_catalog import CropCatalogEntry

__all__ = ["CropCatalogEntry"]
