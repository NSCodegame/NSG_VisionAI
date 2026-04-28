"""Authentication endpoints"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    UserProfile,
)
from app.core.database import get_session
from app.models.user import User, UserRole
from app.services.auth_service import (
    AccountLockedError,
    AuthService,
    AuthenticationError,
    InvalidCredentialsError,
)

# ---------------------------------------------------------------------------
# Demo credentials (used when DB is unavailable — development only)
# ---------------------------------------------------------------------------
_DEMO_USERS = {
    "NSG/ADMIN/0001": {"password": "Admin@NSG2024",    "role": "ADMIN",     "name": "System Administrator", "unit": "NSG IT Cell"},
    "NSG/CMD/0001":   {"password": "Commander@2024",   "role": "COMMANDER", "name": "Commander Demo",       "unit": "SAG"},
    "NSG/ANL/0001":   {"password": "Analyst@2024",     "role": "ANALYST",   "name": "Analyst Demo",         "unit": "Intelligence"},
    "NSG/OP/0001":    {"password": "Operator@2024",    "role": "OPERATOR",  "name": "Operator Demo",        "unit": "SFC"},
}

def _demo_login(service_number: str, password: str) -> LoginResponse:
    """Return a demo JWT-less response for development without a database."""
    import uuid, time
    from app.core.security import create_access_token, create_refresh_token

    user = _DEMO_USERS.get(service_number.upper())
    if not user or user["password"] != password:
        raise InvalidCredentialsError("Invalid credentials")

    uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, service_number))
    profile = UserProfile(
        id=uid,
        service_number=service_number.upper(),
        full_name=user["name"],
        role=user["role"],
        unit=user["unit"],
        is_active=True,
        last_login_at=None,
    )
    access_token = create_access_token(
        subject=uid,
        additional_claims={"service_number": service_number, "role": user["role"], "full_name": user["name"]},
    )
    refresh_token = create_refresh_token(subject=uid)
    return LoginResponse(user=profile, access_token=access_token, refresh_token=refresh_token, token_type="bearer")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with service number and password. Returns JWT tokens and user profile.",
)
async def login(
    request: Request,
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Authenticate user and generate JWT tokens.

    - **service_number**: NSG service number (e.g., NSG/OP/2847)
    - **password**: User password

    Returns:
    - User profile
    - Access token (8-hour expiration)
    - Refresh token (30-day expiration)

    Errors:
    - 401: Invalid credentials or account deactivated
    - 423: Account locked (after 5 failed attempts, locked for 30 minutes)
    """
    auth_service = AuthService(session)

    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user, tokens = await auth_service.authenticate_user(
            service_number=credentials.service_number,
            password=credentials.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Build user profile
        user_profile = UserProfile(
            id=str(user.id),
            service_number=user.service_number,
            full_name=user.full_name,
            role=user.role,
            unit=user.unit,
            is_active=user.is_active,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        )

        return LoginResponse(
            user=user_profile,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
        )

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "message": "Account locked due to multiple failed login attempts",
                "locked_until": e.locked_until.isoformat(),
            },
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token.",
)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Generate new access token from refresh token.

    - **refresh_token**: Valid JWT refresh token

    Returns:
    - New access token (8-hour expiration)

    Errors:
    - 401: Invalid or expired refresh token
    """
    auth_service = AuthService(session)

    try:
        tokens = await auth_service.refresh_access_token(refresh_request.refresh_token)
        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
    description="Logout user and create audit log entry.",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Logout current user.

    Requires authentication (Bearer token).

    Creates audit log entry for logout action.

    Note: Token blacklisting should be implemented with Redis in production.
    """
    auth_service = AuthService(session)

    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await auth_service.logout(
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.get(
    "/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Get profile of currently authenticated user.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile. Requires authentication."""
    return UserProfile(
        id=str(current_user.id),
        service_number=current_user.service_number,
        full_name=current_user.full_name,
        role=current_user.role,
        unit=current_user.unit,
        is_active=current_user.is_active,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Self-register new operator account",
    description="Register a new OPERATOR account. Account is pending admin approval.",
)
async def register(
    request: Request,
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Self-register a new operator account.

    New accounts are created with OPERATOR role and set as inactive
    pending admin approval. An admin must activate the account before
    the user can log in.

    Errors:
    - 400: Passwords don't match, invalid service number format, or account already exists
    """
    from app.core.security import hash_password
    from app.repositories.user import UserRepository
    from app.repositories.audit_log import AuditLogRepository

    # Validate passwords match
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Validate service number format
    if not User.validate_service_number(data.service_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid service number format. Use NSG/UNIT/NUMBER (e.g., NSG/OP/1234)",
        )

    user_repo = UserRepository(session)

    # Check if service number already exists
    existing = await user_repo.get_by_service_number(data.service_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service number already registered",
        )

    # Build full_name with rank if provided
    full_name = data.full_name
    if data.rank:
        full_name = f"{data.rank} {data.full_name}"

    # Create user as OPERATOR, inactive (pending approval)
    user = await user_repo.create(
        service_number=data.service_number,
        full_name=full_name,
        role=UserRole.OPERATOR.value,
        unit=data.unit or "PENDING",
        password_hash=hash_password(data.password),
        is_active=False,   # Requires admin activation
        failed_login_attempts=0,
    )

    # Audit log
    audit_repo = AuditLogRepository(session)
    await audit_repo.create(
        user_id=user.id,
        action="USER_SELF_REGISTERED",
        resource_type="USER",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={
            "service_number": data.service_number,
            "full_name": full_name,
            "rank": data.rank,
            "email": data.email,
        },
    )

    await session.commit()

    return RegisterResponse(
        message="Registration successful. Your account is pending admin approval. Contact NSG IT Cell to activate.",
        service_number=user.service_number,
        full_name=user.full_name,
        role=user.role,
    )
