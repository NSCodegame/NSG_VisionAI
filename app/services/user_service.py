"""User management service"""
import secrets
import string
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user import UserRepository


class UserService:
    """Service for user management operations (ADMIN only)"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def _generate_temporary_password(self, length: int = 12) -> str:
        """
        Generate secure temporary password.

        Args:
            length: Password length (default: 12)

        Returns:
            Random password string
        """
        # Use uppercase, lowercase, digits, and special characters
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(characters) for _ in range(length))
        return password

    async def create_user(
        self,
        service_number: str,
        full_name: str,
        role: UserRole,
        unit: Optional[str],
        created_by: UUID,
        ip_address: Optional[str] = None,
    ) -> tuple[User, str]:
        """
        Create new user with temporary password.

        Args:
            service_number: NSG service number
            full_name: User's full name
            role: User role
            unit: NSG unit assignment
            created_by: Admin user ID creating this user
            ip_address: Client IP address

        Returns:
            Tuple of (User, temporary_password)

        Raises:
            ValueError: If service number format is invalid or already exists
        """
        # Validate service number format
        if not User.validate_service_number(service_number):
            raise ValueError(f"Invalid service number format: {service_number}")

        # Check if service number already exists
        existing_user = await self.user_repo.get_by_service_number(service_number)
        if existing_user:
            raise ValueError(f"Service number already exists: {service_number}")

        # Generate temporary password
        temp_password = self._generate_temporary_password()

        # Hash password
        password_hash = hash_password(temp_password)

        # Create user
        user = await self.user_repo.create(
            service_number=service_number,
            full_name=full_name,
            role=role.value,
            unit=unit,
            password_hash=password_hash,
            is_active=True,
            failed_login_attempts=0,
        )

        # Create audit log entry
        await self.audit_repo.create(
            user_id=created_by,
            action="USER_CREATED",
            resource_type="USER",
            resource_id=user.id,
            ip_address=ip_address,
            details={
                "service_number": service_number,
                "full_name": full_name,
                "role": role.value,
                "unit": unit,
            },
        )

        await self.session.commit()

        return user, temp_password

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        updated_by: UUID,
        ip_address: Optional[str] = None,
    ) -> Optional[User]:
        """
        Update user role.

        Args:
            user_id: User UUID
            new_role: New role
            updated_by: Admin user ID performing update
            ip_address: Client IP address

        Returns:
            Updated user or None if not found
        """
        user = await self.user_repo.get(user_id)
        if user is None:
            return None

        old_role = user.role

        # Update role
        user = await self.user_repo.update(user_id, role=new_role.value)

        # Create audit log entry
        await self.audit_repo.create(
            user_id=updated_by,
            action="USER_ROLE_UPDATED",
            resource_type="USER",
            resource_id=user_id,
            ip_address=ip_address,
            details={
                "old_role": old_role,
                "new_role": new_role.value,
            },
        )

        await self.session.commit()

        return user

    async def deactivate_user(
        self,
        user_id: UUID,
        deactivated_by: UUID,
        ip_address: Optional[str] = None,
    ) -> Optional[User]:
        """
        Deactivate user account (soft delete).

        Args:
            user_id: User UUID
            deactivated_by: Admin user ID performing deactivation
            ip_address: Client IP address

        Returns:
            Updated user or None if not found
        """
        user = await self.user_repo.deactivate(user_id)

        if user:
            # Create audit log entry
            await self.audit_repo.create(
                user_id=deactivated_by,
                action="USER_DEACTIVATED",
                resource_type="USER",
                resource_id=user_id,
                ip_address=ip_address,
                details={
                    "service_number": user.service_number,
                },
            )

            await self.session.commit()

        return user

    async def reset_password(
        self,
        user_id: UUID,
        reset_by: UUID,
        ip_address: Optional[str] = None,
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Reset user password to new temporary password.

        Args:
            user_id: User UUID
            reset_by: Admin user ID performing reset
            ip_address: Client IP address

        Returns:
            Tuple of (User, temporary_password) or (None, None) if user not found
        """
        user = await self.user_repo.get(user_id)
        if user is None:
            return None, None

        # Generate new temporary password
        temp_password = self._generate_temporary_password()

        # Hash password
        password_hash = hash_password(temp_password)

        # Update password and reset failed login attempts
        user = await self.user_repo.update(
            user_id,
            password_hash=password_hash,
            failed_login_attempts=0,
            locked_until=None,
        )

        # Create audit log entry
        await self.audit_repo.create(
            user_id=reset_by,
            action="USER_PASSWORD_RESET",
            resource_type="USER",
            resource_id=user_id,
            ip_address=ip_address,
            details={
                "service_number": user.service_number,
            },
        )

        await self.session.commit()

        return user, temp_password

    async def get_users(
        self,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get users with optional filtering.

        Args:
            role: Filter by role
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of users
        """
        filters = []

        if role is not None:
            filters.append(User.role == role.value)

        if is_active is not None:
            filters.append(User.is_active == is_active)

        return await self.user_repo.get_multi(
            skip=skip,
            limit=limit,
            filters=filters if filters else None,
            order_by=User.created_at.desc(),
        )
