"""REST endpoints for authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_user_agent
from app.database.session import get_db_session
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthService:
    """Build the auth service with a database session."""
    return AuthService(session)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate and issue a JWT token pair."""
    user_agent = get_user_agent(request)
    return await service.login(payload, user_agent)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    user_agent = get_user_agent(request)
    return await service.rotate_refresh_token(payload.refresh_token, user_agent)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    """Revoke a refresh token."""
    await service.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
