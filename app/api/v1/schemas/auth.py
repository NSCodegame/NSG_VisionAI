"""Authentication schemas"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Login request schema"""

    service_number: str = Field(
        ...,
        description="NSG service number (e.g., NSG/OP/2847)",
        min_length=5,
        max_length=50,
    )
    password: str = Field(..., description="User password", min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    """Self-registration request schema"""

    full_name: str = Field(..., description="Full name", min_length=2, max_length=255)
    service_number: str = Field(
        ...,
        description="NSG service number (e.g., NSG/OP/2847)",
        min_length=5,
        max_length=50,
    )
    rank: Optional[str] = Field(None, description="Rank / Designation", max_length=100)
    email: Optional[str] = Field(None, description="Email address", max_length=255)
    unit: Optional[str] = Field(None, description="NSG unit", max_length=100)
    password: str = Field(..., description="Password", min_length=8, max_length=100)
    confirm_password: str = Field(..., description="Confirm password", min_length=8, max_length=100)


class RegisterResponse(BaseModel):
    """Registration response schema"""

    message: str
    service_number: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""

    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserProfile(BaseModel):
    """User profile schema"""

    id: str = Field(..., description="User UUID")
    service_number: str = Field(..., description="NSG service number")
    full_name: str = Field(..., description="Full name")
    role: str = Field(..., description="User role")
    unit: str | None = Field(None, description="NSG unit")
    is_active: bool = Field(..., description="Account active status")
    last_login_at: str | None = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response schema"""

    user: UserProfile = Field(..., description="User profile")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
