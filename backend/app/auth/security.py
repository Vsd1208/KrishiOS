"""Cryptographic security utilities for password hashing and JWT management.

Uses modern standards:
- Argon2id for password hashing
- HS256 for symmetric JWT signatures
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config.settings import get_settings
from app.models.user import UserRole

# ── Password Hashing ───────────────────────────────────────────────────────

# Initialize Argon2id hasher with secure defaults
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(encoded_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(encoded_hash: str) -> bool:
    """Check if the hash needs to be upgraded due to parameter changes."""
    return _hasher.check_needs_rehash(encoded_hash)


# ── JWT Generation and Decoding ────────────────────────────────────────────

def create_access_token(
    user_uuid: UUID,
    role: UserRole,
    permissions: frozenset[str],
    jti: UUID,
) -> str:
    """Create a short-lived stateless JWT for API access."""
    settings = get_settings()
    now = datetime.now(UTC)
    
    # We use 15 minutes TTL for the access token
    expires = now + timedelta(minutes=15)
    
    payload: dict[str, Any] = {
        "sub": str(user_uuid),
        "role": role.value,
        "permissions": list(permissions),
        "jti": str(jti),
        "iat": now,
        "exp": expires,
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.
    
    Raises:
        jwt.ExpiredSignatureError: If the token is expired.
        jwt.InvalidTokenError: If the token is malformed or signature is invalid.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
