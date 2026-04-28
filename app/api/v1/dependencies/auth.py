"""Authentication and authorization dependencies"""
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token, verify_token_type
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        session: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode and validate token
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of allowed user roles

    Returns:
        Dependency function that checks user role

    Example:
        @router.get("/admin", dependencies=[Depends(require_role([UserRole.ADMIN]))])
        async def admin_endpoint():
            ...
    """

    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        """
        Check if current user has required role.

        Args:
            current_user: Current authenticated user

        Returns:
            Current user if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        user_role = UserRole(current_user.role)

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}",
            )

        return current_user

    return check_role


# Convenience dependencies for common role requirements
async def require_operator(current_user: User = Depends(get_current_user)) -> User:
    """Require OPERATOR role or higher"""
    allowed_roles = [UserRole.OPERATOR, UserRole.ANALYST, UserRole.COMMANDER, UserRole.ADMIN]
    return await require_role(allowed_roles)(current_user)


async def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Require ANALYST role or higher"""
    allowed_roles = [UserRole.ANALYST, UserRole.COMMANDER, UserRole.ADMIN]
    return await require_role(allowed_roles)(current_user)


async def require_commander(current_user: User = Depends(get_current_user)) -> User:
    """Require COMMANDER role or higher"""
    allowed_roles = [UserRole.COMMANDER, UserRole.ADMIN]
    return await require_role(allowed_roles)(current_user)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require ADMIN role"""
    allowed_roles = [UserRole.ADMIN]
    return await require_role(allowed_roles)(current_user)


# Optional authentication (returns None if not authenticated)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.

    Args:
        credentials: HTTP Bearer credentials (optional)
        session: Database session

    Returns:
        Current user or None
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None
