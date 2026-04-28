"""User management endpoints (ADMIN only)"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_admin
from app.api.v1.schemas.user import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from app.core.database import get_session
from app.models.user import User, UserRole
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


def _extract_ip_address(request: Request) -> Optional[str]:
    """Extract IP address from request"""
    return request.client.host if request.client else None


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="List users with pagination, filtering, and sorting (ADMIN only)",
)
async def list_users(
    request: Request,
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    List users with optional filtering and pagination.

    Requires ADMIN role.

    Query Parameters:
    - **role**: Filter by user role (OPERATOR, ANALYST, COMMANDER, ADMIN)
    - **is_active**: Filter by active status (true/false)
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records (default: 100, max: 1000)

    Returns:
    - List of users with pagination metadata
    """
    user_service = UserService(session)

    # Get users with filters
    users = await user_service.get_users(
        role=role,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )

    # Count total users with same filters
    filters = []
    if role is not None:
        filters.append(User.role == role.value)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    from app.repositories.user import UserRepository

    user_repo = UserRepository(session)
    total = await user_repo.count(filters=filters if filters else None)

    # Convert to response schema
    user_responses = [
        UserResponse(
            id=str(user.id),
            service_number=user.service_number,
            full_name=user.full_name,
            role=user.role,
            unit=user.unit,
            is_active=user.is_active,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until.isoformat() if user.locked_until else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]

    return UserListResponse(
        users=user_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create new user with temporary password (ADMIN only)",
)
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Create new user account.

    Requires ADMIN role.

    Request Body:
    - **service_number**: NSG service number (e.g., NSG/OP/2847)
    - **full_name**: User's full name
    - **role**: User role (OPERATOR, ANALYST, COMMANDER, ADMIN)
    - **unit**: NSG unit assignment (optional)

    Returns:
    - Created user details
    - Temporary password (shown once, must be changed on first login)

    Errors:
    - 400: Invalid service number format or service number already exists
    """
    user_service = UserService(session)
    ip_address = _extract_ip_address(request)

    try:
        user, temp_password = await user_service.create_user(
            service_number=user_data.service_number,
            full_name=user_data.full_name,
            role=user_data.role,
            unit=user_data.unit,
            created_by=current_user.id,
            ip_address=ip_address,
        )

        user_response = UserResponse(
            id=str(user.id),
            service_number=user.service_number,
            full_name=user.full_name,
            role=user.role,
            unit=user.unit,
            is_active=user.is_active,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until.isoformat() if user.locked_until else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_at=user.created_at.isoformat(),
        )

        return CreateUserResponse(
            user=user_response,
            temporary_password=temp_password,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details",
    description="Get user details by ID (ADMIN only)",
)
async def get_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get user details by ID.

    Requires ADMIN role.

    Path Parameters:
    - **user_id**: User UUID

    Returns:
    - User details

    Errors:
    - 404: User not found
    """
    from app.repositories.user import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return UserResponse(
        id=str(user.id),
        service_number=user.service_number,
        full_name=user.full_name,
        role=user.role,
        unit=user.unit,
        is_active=user.is_active,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until.isoformat() if user.locked_until else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user details (ADMIN only)",
)
async def update_user(
    request: Request,
    user_id: UUID,
    user_data: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user details.

    Requires ADMIN role.

    Path Parameters:
    - **user_id**: User UUID

    Request Body:
    - **full_name**: User's full name (optional)
    - **role**: User role (optional)
    - **unit**: NSG unit assignment (optional)

    Returns:
    - Updated user details

    Errors:
    - 404: User not found
    """
    from app.repositories.user import UserRepository

    user_repo = UserRepository(session)
    ip_address = _extract_ip_address(request)

    # Check if user exists
    user = await user_repo.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    user_service = UserService(session)

    # Update role if provided
    if user_data.role is not None:
        user = await user_service.update_user_role(
            user_id=user_id,
            new_role=user_data.role,
            updated_by=current_user.id,
            ip_address=ip_address,
        )

    # Update other fields if provided
    update_fields = {}
    if user_data.full_name is not None:
        update_fields["full_name"] = user_data.full_name
    if user_data.unit is not None:
        update_fields["unit"] = user_data.unit

    if update_fields:
        user = await user_repo.update(user_id, **update_fields)

        # Create audit log for non-role updates
        from app.repositories.audit_log import AuditLogRepository

        audit_repo = AuditLogRepository(session)
        await audit_repo.create(
            user_id=current_user.id,
            action="USER_UPDATED",
            resource_type="USER",
            resource_id=user_id,
            ip_address=ip_address,
            details=update_fields,
        )

        await session.commit()

    return UserResponse(
        id=str(user.id),
        service_number=user.service_number,
        full_name=user.full_name,
        role=user.role,
        unit=user.unit,
        is_active=user.is_active,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until.isoformat() if user.locked_until else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Soft delete user (set is_active=False) (ADMIN only)",
)
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Soft delete user account (set is_active=False).

    Requires ADMIN role.

    Path Parameters:
    - **user_id**: User UUID

    Returns:
    - 204 No Content on success

    Errors:
    - 404: User not found
    """
    user_service = UserService(session)
    ip_address = _extract_ip_address(request)

    user = await user_service.deactivate_user(
        user_id=user_id,
        deactivated_by=current_user.id,
        ip_address=ip_address,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return None


@router.post(
    "/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset user password",
    description="Reset user password to new temporary password (ADMIN only)",
)
async def reset_password(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Reset user password to new temporary password.

    Requires ADMIN role.

    Path Parameters:
    - **user_id**: User UUID

    Returns:
    - Success message
    - New temporary password

    Errors:
    - 404: User not found
    """
    user_service = UserService(session)
    ip_address = _extract_ip_address(request)

    user, temp_password = await user_service.reset_password(
        user_id=user_id,
        reset_by=current_user.id,
        ip_address=ip_address,
    )

    if user is None or temp_password is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return ResetPasswordResponse(
        message=f"Password reset successful for user {user.service_number}",
        temporary_password=temp_password,
    )
