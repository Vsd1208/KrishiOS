"""Shared SQLAlchemy model mixins for KrishiOS domain entities."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds creation and update timestamps to persistent domain entities."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds reversible deletion metadata without physically removing rows."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Return whether the entity has been soft deleted."""
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        """Mark the entity as deleted using the current UTC timestamp."""
        self.deleted_at = datetime.now(UTC)
