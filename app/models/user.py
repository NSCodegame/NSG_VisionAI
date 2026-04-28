"""User and Authentication Models"""
import re
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, PyEnum):
    """User role enumeration"""

    OPERATOR = "OPERATOR"
    ANALYST = "ANALYST"
    COMMANDER = "COMMANDER"
    ADMIN = "ADMIN"


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    # User identification
    service_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="NSG service number (e.g., NSG/OP/2847)"
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Full name of the user")

    # Role and unit
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="User role (OPERATOR, ANALYST, COMMANDER, ADMIN)"
    )
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="NSG unit assignment")

    # Authentication
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Bcrypt password hash (12 rounds)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="Account active status")

    # Failed login tracking
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Count of consecutive failed login attempts"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Account locked until this timestamp"
    )

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last successful login timestamp"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('OPERATOR', 'ANALYST', 'COMMANDER', 'ADMIN')", name="check_user_role_valid"
        ),
        Index("idx_users_service_number", "service_number"),
        Index("idx_users_role", "role"),
    )

    @staticmethod
    def validate_service_number(service_number: str) -> bool:
        """
        Validate NSG service number format.

        Format: NSG/<UNIT>/<NUMBER>
        Examples: NSG/OP/2847, NSG/SAG/1234, NSG/CMD/5678

        Args:
            service_number: Service number to validate

        Returns:
            True if valid, False otherwise
        """
        pattern = r"^NSG/[A-Z]+/\d+$"
        return bool(re.match(pattern, service_number))

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.now(self.locked_until.tzinfo) < self.locked_until

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<User(id={self.id}, service_number='{self.service_number}', "
            f"role='{self.role}', is_active={self.is_active})>"
        )
