"""User management schemas"""
from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole


class CreateUserRequest(BaseModel):
    """Create user request schema"""

    service_number: str = Field(
        ...,
        description="NSG service number (e.g., NSG/OP/2847)",
        min_length=5,
        max_length=50,
    )
    full_name: str = Field(..., description="Full name", min_length=2, max_length=255)
    role: UserRole = Field(..., description="User role")
    unit: Optional[str] = Field(None, description="NSG unit", max_length=100)


class CreateUserResponse(BaseModel):
    """Create user response schema"""

    user: "UserResponse" = Field(..., description="Created user")
    temporary_password: str = Field(
        ..., description="Temporary password (shown once, must be changed on first login)"
    )


class UpdateUserRequest(BaseModel):
    """Update user request schema"""

    full_name: Optional[str] = Field(None, description="Full name", min_length=2, max_length=255)
    role: Optional[UserRole] = Field(None, description="User role")
    unit: Optional[str] = Field(None, description="NSG unit", max_length=100)


class ResetPasswordResponse(BaseModel):
    """Reset password response schema"""

    message: str = Field(..., description="Success message")
    temporary_password: str = Field(..., description="New temporary password")


class UserResponse(BaseModel):
    """User response schema"""

    id: str = Field(..., description="User UUID")
    service_number: str = Field(..., description="NSG service number")
    full_name: str = Field(..., description="Full name")
    role: str = Field(..., description="User role")
    unit: Optional[str] = Field(None, description="NSG unit")
    is_active: bool = Field(..., description="Account active status")
    failed_login_attempts: int = Field(..., description="Failed login attempts")
    locked_until: Optional[str] = Field(None, description="Account locked until timestamp")
    last_login_at: Optional[str] = Field(None, description="Last login timestamp")
    created_at: str = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response schema"""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
