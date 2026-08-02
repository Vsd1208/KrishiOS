"""Authentication and authorization models for KrishiOS Sprint 5.

Two tables:
  User         — the authentication identity.
  RefreshToken — stateful refresh token lifecycle management.

Design rationale:
  The existing Farmer and Officer models store domain-specific data
  (landholding, district, designation) that has nothing to do with
  authentication. Rather than polluting those models with password hashes
  or tokens, a separate User table holds the identity credential and links
  back to the relevant domain profile via nullable FK.

  This keeps auth concerns separate from agricultural domain concerns,
  which matches the repository's existing separation of services.
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    """Roles supported by the KrishiOS RBAC system."""

    FARMER = "farmer"
    OFFICER = "officer"
    AGRONOMIST = "agronomist"
    ADMIN = "admin"
    SYSTEM = "system"


class User(TimestampMixin, Base):
    """Authentication identity for all KrishiOS actors.

    Deliberately minimal: stores only what is required for authentication
    and role-based authorization. Domain profile data (landholding, district
    designation, etc.) lives in Farmer / Officer tables and is linked via FK.
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Credentials ──────────────────────────────────────────────────────────
    # At least one of phone / email must be present; enforced at the service layer.
    phone: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Argon2id hash — never logged or returned via API",
    )

    # ── Authorization ─────────────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.FARMER,
        index=True,
    )

    # ── Account state ─────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Domain profile links (nullable — not all users have a domain profile) ─
    farmer_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("farmer.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    officer_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("officer.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_user_role_active", "role", "is_active"),
    )


class RefreshToken(Base):
    """Stateful refresh token record enabling rotation and revocation.

    The JWT itself is stateless; the jti (JWT ID) stored here is the
    authoritative record. Revocation means setting revoked_at; this is
    checked before issuing a new access token.
    """

    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jti: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="JWT ID — uniquely identifies this token for revocation",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Null means the token is still valid",
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_token_user_active", "user_id", "revoked_at"),
    )
