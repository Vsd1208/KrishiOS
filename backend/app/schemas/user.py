"""User schemas for registration and API responses."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Payload to create a new identity."""
    
    phone: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.FARMER
    
    farmer_profile_id: int | None = None
    officer_profile_id: int | None = None


class UserResponse(BaseModel):
    """API representation of a user identity."""
    
    model_config = ConfigDict(from_attributes=True)
    
    uuid: UUID
    phone: str | None
    email: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    
    farmer_profile_id: int | None
    officer_profile_id: int | None
    created_at: datetime
    updated_at: datetime
