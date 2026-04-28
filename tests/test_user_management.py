"""
Integration tests for user management functionality.

Tests cover:
- User CRUD operations (list, create, get, update, delete)
- Role-based access control (RBAC)
- Temporary password generation
- User deactivation and login prevention
- Audit log entries
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.user import UserRepository




@pytest.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing"""
    user_repo = UserRepository(db_session)
    
    admin = await user_repo.create(
        service_number="NSG/ADMIN/0001",
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        unit="HQ",
        password_hash=hash_password("admin123"),
        is_active=True,
        failed_login_attempts=0,
    )
    
    await db_session.commit()
    return admin


@pytest.fixture(scope="function")
async def operator_user(db_session: AsyncSession) -> User:
    """Create operator user for testing"""
    user_repo = UserRepository(db_session)
    
    operator = await user_repo.create(
        service_number="NSG/OP/1001",
        full_name="Test Operator",
        role=UserRole.OPERATOR.value,
        unit="SAG",
        password_hash=hash_password("operator123"),
        is_active=True,
        failed_login_attempts=0,
    )
    
    await db_session.commit()
    return operator


@pytest.fixture(scope="function")
def admin_token(admin_user: User) -> str:
    """Generate JWT token for admin user"""
    return create_access_token({"sub": str(admin_user.id), "role": admin_user.role})


@pytest.fixture(scope="function")
def operator_token(operator_user: User) -> str:
    """Generate JWT token for operator user"""
    return create_access_token({"sub": str(operator_user.id), "role": operator_user.role})


# ============================================================================
# Test User CRUD Operations
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestUserCRUD:
    """Test user CRUD operations"""
    
    async def test_list_users_success(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        operator_user: User,
    ):
        """Test GET /api/v1/users - list users with pagination"""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        
        assert data["total"] >= 2  # At least admin and operator
        assert len(data["users"]) >= 2
        assert data["skip"] == 0
        assert data["limit"] == 100
    
    async def test_list_users_with_role_filter(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        operator_user: User,
    ):
        """Test GET /api/v1/users with role filter"""
        response = await client.get(
            "/api/v1/users?role=ADMIN",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        for user in data["users"]:
            assert user["role"] == "ADMIN"
    
    async def test_list_users_with_pagination(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
    ):
        """Test GET /api/v1/users with pagination parameters"""
        response = await client.get(
            "/api/v1/users?skip=0&limit=1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["skip"] == 0
        assert data["limit"] == 1
        assert len(data["users"]) <= 1
    
    async def test_create_user_success(
        self,
        client: AsyncClient,
        admin_token: str,
        db_session: AsyncSession,
    ):
        """Test POST /api/v1/users - create user with temp password"""
        user_data = {
            "service_number": "NSG/OP/9999",
            "full_name": "New Test User",
            "role": "OPERATOR",
            "unit": "SAG",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "user" in data
        assert "temporary_password" in data
        
        user = data["user"]
        assert user["service_number"] == "NSG/OP/9999"
        assert user["full_name"] == "New Test User"
        assert user["role"] == "OPERATOR"
        assert user["unit"] == "SAG"
        assert user["is_active"] is True
        
        # Verify temp password format
        temp_password = data["temporary_password"]
        assert len(temp_password) == 12
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
    
    async def test_create_user_invalid_service_number(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test POST /api/v1/users with invalid service number format"""
        user_data = {
            "service_number": "INVALID",
            "full_name": "Test User",
            "role": "OPERATOR",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 400
        assert "Invalid service number format" in response.json()["detail"]
    
    async def test_create_user_duplicate_service_number(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
    ):
        """Test POST /api/v1/users with duplicate service number"""
        user_data = {
            "service_number": operator_user.service_number,
            "full_name": "Duplicate User",
            "role": "OPERATOR",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    async def test_get_user_success(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
    ):
        """Test GET /api/v1/users/{id} - get user details"""
        response = await client.get(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(operator_user.id)
        assert data["service_number"] == operator_user.service_number
        assert data["full_name"] == operator_user.full_name
        assert data["role"] == operator_user.role
    
    async def test_get_user_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test GET /api/v1/users/{id} with non-existent user"""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 404
    
    async def test_update_user_success(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test PUT /api/v1/users/{id} - update user"""
        update_data = {
            "full_name": "Updated Name",
            "role": "ANALYST",
            "unit": "Updated Unit",
        }
        
        response = await client.put(
            f"/api/v1/users/{operator_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "ANALYST"
        assert data["unit"] == "Updated Unit"
    
    async def test_update_user_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test PUT /api/v1/users/{id} with non-existent user"""
        fake_id = uuid4()
        update_data = {"full_name": "Updated Name"}
        
        response = await client.put(
            f"/api/v1/users/{fake_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 404
    
    async def test_delete_user_success(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test DELETE /api/v1/users/{id} - soft delete"""
        response = await client.delete(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 204
        
        # Verify user is deactivated
        user_repo = UserRepository(db_session)
        user = await user_repo.get(operator_user.id)
        assert user is not None
        assert user.is_active is False
    
    async def test_delete_user_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test DELETE /api/v1/users/{id} with non-existent user"""
        fake_id = uuid4()
        response = await client.delete(
            f"/api/v1/users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 404
    
    async def test_reset_password_success(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
    ):
        """Test POST /api/v1/users/{id}/reset-password"""
        response = await client.post(
            f"/api/v1/users/{operator_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "temporary_password" in data
        
        # Verify temp password format
        temp_password = data["temporary_password"]
        assert len(temp_password) == 12
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
    
    async def test_reset_password_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test POST /api/v1/users/{id}/reset-password with non-existent user"""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/users/{fake_id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 404


# ============================================================================
# Test Role-Based Access Control (RBAC)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestRBAC:
    """Test role-based access control for user management endpoints"""
    
    async def test_non_admin_list_users_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
    ):
        """Test non-admin user gets 403 on GET /api/v1/users"""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    async def test_non_admin_create_user_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
    ):
        """Test non-admin user gets 403 on POST /api/v1/users"""
        user_data = {
            "service_number": "NSG/OP/8888",
            "full_name": "Test User",
            "role": "OPERATOR",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
    
    async def test_non_admin_get_user_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
        admin_user: User,
    ):
        """Test non-admin user gets 403 on GET /api/v1/users/{id}"""
        response = await client.get(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
    
    async def test_non_admin_update_user_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
        admin_user: User,
    ):
        """Test non-admin user gets 403 on PUT /api/v1/users/{id}"""
        update_data = {"full_name": "Updated Name"}
        
        response = await client.put(
            f"/api/v1/users/{admin_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
    
    async def test_non_admin_delete_user_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
        admin_user: User,
    ):
        """Test non-admin user gets 403 on DELETE /api/v1/users/{id}"""
        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
    
    async def test_non_admin_reset_password_forbidden(
        self,
        client: AsyncClient,
        operator_token: str,
        admin_user: User,
    ):
        """Test non-admin user gets 403 on POST /api/v1/users/{id}/reset-password"""
        response = await client.post(
            f"/api/v1/users/{admin_user.id}/reset-password",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
    
    async def test_unauthenticated_access_forbidden(
        self,
        client: AsyncClient,
    ):
        """Test unauthenticated request gets 401/403"""
        response = await client.get("/api/v1/users")
        
        assert response.status_code in [401, 403]


# ============================================================================
# Test Temporary Password Generation
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestTemporaryPassword:
    """Test temporary password generation and format"""
    
    async def test_temp_password_on_user_creation(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test temp password is returned on user creation"""
        user_data = {
            "service_number": "NSG/OP/7777",
            "full_name": "Temp Password Test",
            "role": "OPERATOR",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "temporary_password" in data
        temp_password = data["temporary_password"]
        
        # Verify password strength
        assert len(temp_password) >= 12
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
        assert any(c in "!@#$%^&*" for c in temp_password)
    
    async def test_temp_password_on_reset(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
    ):
        """Test temp password is returned on password reset"""
        response = await client.post(
            f"/api/v1/users/{operator_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "temporary_password" in data
        temp_password = data["temporary_password"]
        
        # Verify password strength
        assert len(temp_password) >= 12
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
        assert any(c in "!@#$%^&*" for c in temp_password)
    
    async def test_temp_password_format_and_strength(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """Test temp password meets security requirements"""
        # Create multiple users to test password randomness
        passwords = []
        
        for i in range(3):
            user_data = {
                "service_number": f"NSG/OP/666{i}",
                "full_name": f"Password Test {i}",
                "role": "OPERATOR",
            }
            
            response = await client.post(
                "/api/v1/users",
                json=user_data,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            
            assert response.status_code == 201
            passwords.append(response.json()["temporary_password"])
        
        # Verify all passwords are different (randomness)
        assert len(set(passwords)) == 3
        
        # Verify each password meets requirements
        for password in passwords:
            assert len(password) == 12
            assert any(c.isupper() for c in password)
            assert any(c.islower() for c in password)
            assert any(c.isdigit() for c in password)


# ============================================================================
# Test User Deactivation Prevents Login
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestUserDeactivation:
    """Test that deactivated users cannot login"""
    
    async def test_deactivated_user_cannot_login(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test deactivated user cannot authenticate"""
        # Deactivate user
        response = await client.delete(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204
        
        # Attempt to login
        login_data = {
            "service_number": operator_user.service_number,
            "password": "operator123",
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "deactivated" in response.json()["detail"].lower()
    
    async def test_is_active_false_after_deletion(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test is_active=False after soft delete"""
        # Delete user
        response = await client.delete(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204
        
        # Verify is_active is False
        user_repo = UserRepository(db_session)
        user = await user_repo.get(operator_user.id)
        
        assert user is not None
        assert user.is_active is False
    
    async def test_deactivated_user_with_valid_token_forbidden(
        self,
        client: AsyncClient,
        admin_token: str,
        operator_user: User,
        operator_token: str,
    ):
        """Test deactivated user with valid token gets 403"""
        # Deactivate user
        response = await client.delete(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204
        
        # Try to access endpoint with old token
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


# ============================================================================
# Test Audit Log Entries
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestAuditLogs:
    """Test audit log entries are created for user management actions"""
    
    async def test_audit_log_user_creation(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        db_session: AsyncSession,
    ):
        """Test audit log for user creation"""
        user_data = {
            "service_number": "NSG/OP/5555",
            "full_name": "Audit Test User",
            "role": "OPERATOR",
            "unit": "SAG",
        }
        
        response = await client.post(
            "/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        
        # Check audit log
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(
            filters=[AuditLog.action == "USER_CREATED"],
            order_by=AuditLog.created_at.desc(),
            limit=1,
        )
        
        assert len(logs) > 0
        log = logs[0]
        assert log.action == "USER_CREATED"
        assert log.user_id == admin_user.id
        assert log.resource_type == "USER"
        assert log.details["service_number"] == "NSG/OP/5555"
    
    async def test_audit_log_role_update(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test audit log for role updates"""
        update_data = {"role": "ANALYST"}
        
        response = await client.put(
            f"/api/v1/users/{operator_user.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        # Check audit log
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(
            filters=[AuditLog.action == "USER_ROLE_UPDATED"],
            order_by=AuditLog.created_at.desc(),
            limit=1,
        )
        
        assert len(logs) > 0
        log = logs[0]
        assert log.action == "USER_ROLE_UPDATED"
        assert log.user_id == admin_user.id
        assert log.resource_id == operator_user.id
        assert log.details["old_role"] == "OPERATOR"
        assert log.details["new_role"] == "ANALYST"
    
    async def test_audit_log_user_deactivation(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test audit log for user deactivation"""
        response = await client.delete(
            f"/api/v1/users/{operator_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204
        
        # Check audit log
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(
            filters=[AuditLog.action == "USER_DEACTIVATED"],
            order_by=AuditLog.created_at.desc(),
            limit=1,
        )
        
        assert len(logs) > 0
        log = logs[0]
        assert log.action == "USER_DEACTIVATED"
        assert log.user_id == admin_user.id
        assert log.resource_id == operator_user.id
        assert log.details["service_number"] == operator_user.service_number
    
    async def test_audit_log_password_reset(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        operator_user: User,
        db_session: AsyncSession,
    ):
        """Test audit log for password reset"""
        response = await client.post(
            f"/api/v1/users/{operator_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        # Check audit log
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(
            filters=[AuditLog.action == "USER_PASSWORD_RESET"],
            order_by=AuditLog.created_at.desc(),
            limit=1,
        )
        
        assert len(logs) > 0
        log = logs[0]
        assert log.action == "USER_PASSWORD_RESET"
        assert log.user_id == admin_user.id
        assert log.resource_id == operator_user.id
        assert log.details["service_number"] == operator_user.service_number
