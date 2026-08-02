"""Refresh token repository."""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Persistence operations for refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_jti(self, jti: UUID) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        return await self._scalar_one_or_none(statement)
