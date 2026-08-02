"""Authentication payloads and token responses."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Payload to exchange credentials for a token pair."""
    phone: str | None = None
    email: EmailStr | None = None
    password: str


class RefreshRequest(BaseModel):
    """Payload to rotate a refresh token."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token pair returned upon successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
