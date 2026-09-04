"""Authentication service.

Handles exchanging credentials for tokens, and rotating refresh tokens.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_permissions_for_role
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
    needs_rehash,
)
from app.models.user import RefreshToken, User, UserRole
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.base import BaseService


class AuthService(BaseService):
    """Business logic for authentication and token lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def login(self, payload: LoginRequest, user_agent: str | None = None) -> TokenResponse:
        """Authenticate a user and issue a token pair."""
        if not payload.phone and not payload.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either phone or email must be provided",
            )

        # 1. Lookup user
        user = None
        if payload.phone:
            user = await self.users.get_by_phone(payload.phone)
        elif payload.email:
            user = await self.users.get_by_email(payload.email)

        # 2. Verify existence and password
        if user is None or not verify_password(payload.password, user.password_hash):
            logger.warning("Failed login attempt")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning("Attempted login to inactive account: {}", user.uuid)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # 3. Transparently upgrade hash if parameters changed
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)

        # 4. Update login metadata
        user.last_login = datetime.now(UTC)

        # 5. Issue tokens
        return await self._issue_token_pair(user, user_agent)

    async def rotate_refresh_token(
        self,
        token_str: str,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Exchange a valid refresh token for a new token pair."""
        try:
            # We expect the refresh token to just be the UUID string of the JTI
            jti = uuid.UUID(token_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token format",
            )

        # 1. Lookup token
        token_record = await self.refresh_tokens.get_by_jti(jti)
        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found",
            )

        # 2. Check if revoked or expired
        now = datetime.now(UTC)
        if token_record.revoked_at is not None or token_record.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is expired or revoked",
            )

        # 3. Revoke the old token (rotation)
        token_record.revoked_at = now

        # 4. Get the user
        user = await self.users.get(token_record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or deleted",
            )

        # 5. Issue new pair
        return await self._issue_token_pair(user, user_agent)

    async def logout(self, token_str: str) -> None:
        """Revoke a refresh token."""
        try:
            jti = uuid.UUID(token_str)
        except ValueError:
            return  # Fail silently on logout

        token_record = await self.refresh_tokens.get_by_jti(jti)
        if token_record and token_record.revoked_at is None:
            token_record.revoked_at = datetime.now(UTC)
            await self._commit()

    async def _issue_token_pair(self, user: User, user_agent: str | None) -> TokenResponse:
        now = datetime.now(UTC)
        
        # 1. Create Refresh Token record
        jti = uuid.uuid4()
        refresh_expires = now + timedelta(days=7)
        
        token_record = RefreshToken(
            jti=jti,
            user_id=user.id,
            issued_at=now,
            expires_at=refresh_expires,
            user_agent=user_agent,
        )
        self.session.add(token_record)
        
        # 2. Create Access Token (stateless)
        permissions = get_permissions_for_role(user.role)
        access_token = create_access_token(
            user_uuid=user.uuid,
            role=UserRole(user.role),
            permissions=permissions,
            jti=jti,
        )
        
        await self._commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=str(jti),
        )
