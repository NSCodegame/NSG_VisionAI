"""
Tests for Video Feed API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.video_feed import FeedType, VideoFeed
from app.repositories.user import UserRepository
from app.repositories.video_feed import VideoFeedRepository
from app.services.auth_service import AuthService
from app.utils.encryption import encrypt_rtsp_url
from app.core.config import settings


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing"""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        service_number="NSG/ADMIN/9999",
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    await db_session.commit()
    return user


@pytest.fixture
async def operator_user(db_session: AsyncSession) -> User:
    """Create operator user for testing"""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        service_number="NSG/OP/8888",
        full_name="Test Operator",
        role=UserRole.OPERATOR.value,
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    await db_session.commit()
    return user


@pytest.fixture
async def admin_token(db_session: AsyncSession, admin_user: User) -> str:
    """Generate admin access token"""
    auth_service = AuthService(db_session)
    _, tokens = await auth_service.authenticate_user(
        service_number="NSG/ADMIN/9999",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def operator_token(db_session: AsyncSession, operator_user: User) -> str:
    """Generate operator access token"""
    auth_service = AuthService(db_session)
    _, tokens = await auth_service.authenticate_user(
        service_number="NSG/OP/8888",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def sample_feed(db_session: AsyncSession) -> VideoFeed:
    """Create sample video feed for testing"""
    feed_repo = VideoFeedRepository(db_session)
    encrypted_url = encrypt_rtsp_url("rtsp://admin:pass@192.168.1.100:554/stream", settings.encryption_master_key)
    feed = await feed_repo.create(
        name="Test Camera 1",
        feed_type=FeedType.FIXED_CAMERA.value,
        rtsp_url_encrypted=encrypted_url,
        status="OFFLINE",
        ai_enabled=True,
    )
    await db_session.commit()
    return feed


class TestListFeeds:
    """Tests for GET /api/v1/feeds"""

    async def test_list_feeds_as_operator(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test listing feeds as operator"""
        response = await client.get(
            "/api/v1/feeds",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "feeds" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["feeds"]) >= 1
        # Check RTSP URL is masked for operator
        assert data["feeds"][0]["rtsp_url"] == "rtsp://***:***@***:***/**"

    async def test_list_feeds_as_admin(
        self, client: AsyncClient, admin_token: str, sample_feed: VideoFeed
    ):
        """Test listing feeds as admin"""
        response = await client.get(
            "/api/v1/feeds",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "feeds" in data
        # Check RTSP URL shows encrypted indicator for admin
        assert data["feeds"][0]["rtsp_url"] == "[ENCRYPTED]"

    async def test_list_feeds_with_filters(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test listing feeds with filters"""
        response = await client.get(
            "/api/v1/feeds?feed_type=FIXED_CAMERA&status=OFFLINE",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_feeds_unauthorized(self, client: AsyncClient):
        """Test listing feeds without authentication"""
        response = await client.get("/api/v1/feeds")
        assert response.status_code == 401


class TestCreateFeed:
    """Tests for POST /api/v1/feeds"""

    async def test_create_feed_as_admin(
        self, client: AsyncClient, admin_token: str
    ):
        """Test creating feed as admin"""
        feed_data = {
            "name": "New Camera",
            "feed_type": "FIXED_CAMERA",
            "rtsp_url": "rtsp://admin:pass@192.168.1.101:554/stream",
            "ai_enabled": True,
        }
        response = await client.post(
            "/api/v1/feeds",
            json=feed_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Camera"
        assert data["feed_type"] == "FIXED_CAMERA"
        assert data["rtsp_url"] == "[ENCRYPTED]"  # Admin sees encrypted indicator

    async def test_create_feed_as_operator_forbidden(
        self, client: AsyncClient, operator_token: str
    ):
        """Test creating feed as operator (should fail)"""
        feed_data = {
            "name": "New Camera",
            "feed_type": "FIXED_CAMERA",
            "rtsp_url": "rtsp://admin:pass@192.168.1.101:554/stream",
            "ai_enabled": True,
        }
        response = await client.post(
            "/api/v1/feeds",
            json=feed_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403

    async def test_create_feed_invalid_rtsp_url(
        self, client: AsyncClient, admin_token: str
    ):
        """Test creating feed with invalid RTSP URL"""
        feed_data = {
            "name": "New Camera",
            "feed_type": "FIXED_CAMERA",
            "rtsp_url": "http://invalid-url",
            "ai_enabled": True,
        }
        response = await client.post(
            "/api/v1/feeds",
            json=feed_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400


class TestGetFeed:
    """Tests for GET /api/v1/feeds/{feed_id}"""

    async def test_get_feed_as_operator(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test getting feed details as operator"""
        response = await client.get(
            f"/api/v1/feeds/{sample_feed.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_feed.id)
        assert data["name"] == sample_feed.name
        # Check RTSP URL is masked for operator
        assert data["rtsp_url"] == "rtsp://***:***@***:***/**"

    async def test_get_feed_not_found(
        self, client: AsyncClient, operator_token: str
    ):
        """Test getting non-existent feed"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/feeds/{fake_uuid}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 404


class TestUpdateFeed:
    """Tests for PUT /api/v1/feeds/{feed_id}"""

    async def test_update_feed_as_admin(
        self, client: AsyncClient, admin_token: str, sample_feed: VideoFeed
    ):
        """Test updating feed as admin"""
        update_data = {
            "name": "Updated Camera Name",
            "location_name": "Building A",
        }
        response = await client.put(
            f"/api/v1/feeds/{sample_feed.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Camera Name"
        assert data["location_name"] == "Building A"

    async def test_update_feed_as_operator_forbidden(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test updating feed as operator (should fail)"""
        update_data = {"name": "Updated Camera Name"}
        response = await client.put(
            f"/api/v1/feeds/{sample_feed.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403


class TestDeleteFeed:
    """Tests for DELETE /api/v1/feeds/{feed_id}"""

    async def test_delete_feed_as_admin(
        self, client: AsyncClient, admin_token: str, sample_feed: VideoFeed
    ):
        """Test deleting feed as admin"""
        response = await client.delete(
            f"/api/v1/feeds/{sample_feed.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

    async def test_delete_feed_as_operator_forbidden(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test deleting feed as operator (should fail)"""
        response = await client.delete(
            f"/api/v1/feeds/{sample_feed.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403


class TestToggleAI:
    """Tests for POST /api/v1/feeds/{feed_id}/toggle-ai"""

    async def test_toggle_ai_as_operator(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test toggling AI processing as operator"""
        response = await client.post(
            f"/api/v1/feeds/{sample_feed.id}/toggle-ai",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # AI should be toggled from True to False
        assert data["ai_enabled"] == False


class TestConnectionTest:
    """Tests for POST /api/v1/feeds/test"""

    async def test_test_connection_as_admin(
        self, client: AsyncClient, admin_token: str
    ):
        """Test RTSP connection test as admin"""
        test_data = {
            "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
            "timeout": 5,
        }
        response = await client.post(
            "/api/v1/feeds/test",
            json=test_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data

    async def test_test_connection_as_operator_forbidden(
        self, client: AsyncClient, operator_token: str
    ):
        """Test RTSP connection test as operator (should fail)"""
        test_data = {
            "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
            "timeout": 5,
        }
        response = await client.post(
            "/api/v1/feeds/test",
            json=test_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403


class TestFeedStats:
    """Tests for GET /api/v1/feeds/{feed_id}/stats"""

    async def test_get_feed_stats_as_operator(
        self, client: AsyncClient, operator_token: str, sample_feed: VideoFeed
    ):
        """Test getting feed statistics as operator"""
        response = await client.get(
            f"/api/v1/feeds/{sample_feed.id}/stats",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "feed_id" in data
        assert "detection_count" in data
        assert "uptime_percentage" in data
        assert data["feed_id"] == str(sample_feed.id)
