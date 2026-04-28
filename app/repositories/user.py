"""User repository"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication-specific methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_service_number(self, service_number: str) -> Optional[User]:
        """
        Get user by service number.

        Args:
            service_number: NSG service number (e.g., NSG/OP/2847)

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.service_number == service_number)
        )
        return result.scalar_one_or_none()

    async def increment_failed_login(self, user_id: UUID) -> User:
        """
        Increment failed login attempts counter.

        Args:
            user_id: User UUID

        Returns:
            Updated user instance
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.failed_login_attempts += 1
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def lock_account(self, user_id: UUID, duration_minutes: int = 30) -> User:
        """
        Lock user account for specified duration.

        Args:
            user_id: User UUID
            duration_minutes: Lock duration in minutes (default: 30)

        Returns:
            Updated user instance
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def reset_failed_login(self, user_id: UUID) -> User:
        """
        Reset failed login attempts counter and unlock account.

        Args:
            user_id: User UUID

        Returns:
            Updated user instance
        """
        user = await self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_role(self, role: UserRole, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get users by role with pagination.

        Args:
            role: User role
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[User.role == role.value],
            order_by=User.created_at.desc(),
        )

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get active users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of active users
        """
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[User.is_active == True],
            order_by=User.created_at.desc(),
        )

    async def deactivate(self, user_id: UUID) -> Optional[User]:
        """
        Deactivate user account (soft delete).

        Args:
            user_id: User UUID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update(user_id, is_active=False)

    async def activate(self, user_id: UUID) -> Optional[User]:
        """
        Activate user account.

        Args:
            user_id: User UUID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update(user_id, is_active=True)
