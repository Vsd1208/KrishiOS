"""FastAPI dependencies for authentication and authorization.

These dependencies extract the JWT, verify it statelessly, and construct
an AuthContext that downstream services and routes can use.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.auth.security import decode_access_token
from app.models.user import UserRole
from app.schemas.auth import TokenResponse

# Standard OAuth2 Bearer token extraction
oauth2_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    """Carries the authenticated identity and capabilities."""

    def __init__(
        self,
        user_uuid: UUID,
        role: UserRole,
        permissions: frozenset[str],
        jti: UUID,
    ) -> None:
        self.user_uuid = user_uuid
        self.role = role
        self.permissions = permissions
        self.jti = jti

    def has_permission(self, required: str) -> bool:
        """Check if the identity holds a specific permission."""
        return required in self.permissions


async def get_current_auth_context(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(oauth2_scheme)],
) -> AuthContext:
    """Extract and verify the JWT, returning the AuthContext.
    
    Raises 401 if the token is missing, invalid, or expired.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token.credentials)
        return AuthContext(
            user_uuid=UUID(payload["sub"]),
            role=UserRole(payload["role"]),
            permissions=frozenset(payload.get("permissions", [])),
            jti=UUID(payload["jti"]),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError, KeyError) as e:
        logger.warning("Invalid token presented: {}", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RequirePermission:
    """Dependency generator for RBAC authorization checks.
    
    Usage:
        @router.get("/something", dependencies=[Depends(RequirePermission(Permission.FARMER_READ))])
    """

    def __init__(self, required_permission: str) -> None:
        self.required_permission = required_permission

    def __call__(self, context: Annotated[AuthContext, Depends(get_current_auth_context)]) -> AuthContext:
        if not context.has_permission(self.required_permission):
            logger.warning(
                "Access denied: User {} lacks permission {}",
                context.user_uuid,
                self.required_permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return context


def get_client_ip(request: Request) -> str | None:
    """Extract client IP for audit logging."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    """Extract user agent for token tracking."""
    return request.headers.get("user-agent")
