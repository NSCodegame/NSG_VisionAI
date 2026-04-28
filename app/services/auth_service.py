"""Authentication service"""
from datetime import datetime
from typing import Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    verify_token_type,
)
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user import UserRepository


class AuthenticationError(Exception):
    """Base exception for authentication errors"""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid"""

    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked"""

    def __init__(self, locked_until: datetime):
        self.locked_until = locked_until
        super().__init__(f"Account locked until {locked_until}")


class AuthService:
    """Authentication service for user login and token management"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def authenticate_user(
        self,
        service_number: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, Dict[str, str]]:
        """
        Authenticate user and generate tokens.

        Args:
            service_number: NSG service number
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (User, tokens_dict)

        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
        """
        # Validate service number format
        if not User.validate_service_number(service_number):
            raise InvalidCredentialsError("Invalid service number format")

        # Get user by service number
        user = await self.user_repo.get_by_service_number(service_number)
        if user is None:
            raise InvalidCredentialsError("Invalid credentials")

        # Check if account is locked
        if user.is_locked:
            raise AccountLockedError(user.locked_until)

        # Check if account is active
        if not user.is_active:
            raise InvalidCredentialsError("Account is deactivated")

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            await self.user_repo.increment_failed_login(user.id)

            # Lock account after 5 failed attempts
            if user.failed_login_attempts + 1 >= settings.account_lockout_attempts:
                await self.user_repo.lock_account(
                    user.id, duration_minutes=settings.account_lockout_duration // 60
                )
                await self.session.commit()
                raise AccountLockedError(
                    datetime.utcnow()
                    + timedelta(seconds=settings.account_lockout_duration)
                )

            await self.session.commit()
            raise InvalidCredentialsError(
                f"Invalid credentials. {settings.account_lockout_attempts - (user.failed_login_attempts + 1)} attempts remaining."
            )

        # Reset failed login attempts on successful authentication
        user = await self.user_repo.reset_failed_login(user.id)

        # Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "service_number": user.service_number,
                "role": user.role,
                "full_name": user.full_name,
            },
        )

        refresh_token = create_refresh_token(subject=str(user.id))

        # Create audit log entry
        await self.audit_repo.create(
            user_id=user.id,
            action="USER_LOGIN",
            resource_type="USER",
            resource_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "service_number": user.service_number,
                "success": True,
            },
        )

        await self.session.commit()

        return user, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new access token

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            payload = decode_token(refresh_token)
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")

        # Verify token type
        if not verify_token_type(payload, "refresh"):
            raise AuthenticationError("Invalid token type")

        # Get user
        user_id = UUID(payload.get("sub"))
        user = await self.user_repo.get(user_id)

        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Generate new access token
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "service_number": user.service_number,
                "role": user.role,
                "full_name": user.full_name,
            },
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def logout(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Logout user and create audit log entry.

        Note: Token blacklisting should be implemented with Redis in production.

        Args:
            user_id: User UUID
            ip_address: Client IP address
            user_agent: Client user agent
        """
        # Create audit log entry
        await self.audit_repo.create(
            user_id=user_id,
            action="USER_LOGOUT",
            resource_type="USER",
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"success": True},
        )

        await self.session.commit()

        # TODO: Implement token blacklisting with Redis
        # redis_client.setex(f"blacklist:{token}", expiration, "1")


from datetime import timedelta
