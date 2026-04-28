"""
Integration tests for video feed and RTSP URL encryption functionality
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.config import settings
from app.core.security import hash_password
from app.models.security_zone import SecurityZone, ThreatLevel, ZoneType
from app.models.user import User, UserRole
from app.models.video_feed import FeedStatus, FeedType, VideoFeed
from app.repositories.audit_log import AuditLogRepository
from app.repositories.security_zone import SecurityZoneRepository
from app.repositories.user import UserRepository
from app.repositories.video_feed import VideoFeedRepository
from app.services.auth_service import AuthService
from app.services.feed_service import FeedService
from app.utils.encryption import decrypt_rtsp_url, encrypt_rtsp_url


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing"""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        service_number="NSG/ADMIN/TEST1",
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
        service_number="NSG/OP/TEST1",
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
        service_number="NSG/ADMIN/TEST1",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def operator_token(db_session: AsyncSession, operator_user: User) -> str:
    """Generate operator access token"""
    auth_service = AuthService(db_session)
    _, tokens = await auth_service.authenticate_user(
        service_number="NSG/OP/TEST1",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def test_zone(db_session: AsyncSession) -> SecurityZone:
    """Create test security zone"""
    zone_repo = SecurityZoneRepository(db_session)
    zone = await zone_repo.create(
        name="Test Zone",
        zone_type=ZoneType.PERIMETER.value,
        polygon_coordinates={
            "type": "Polygon",
            "coordinates": [
                [
                    {"lat": 28.6139, "lng": 77.2090},
                    {"lat": 28.6140, "lng": 77.2091},
                    {"lat": 28.6141, "lng": 77.2089},
                    {"lat": 28.6139, "lng": 77.2090},
                ]
            ],
        },
        threat_level=ThreatLevel.GREEN.value,
    )
    await db_session.commit()
    return zone


class TestFeedCRUDOperations:
    """Integration tests for feed CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_feed_with_encrypted_rtsp_url(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test create feed with encrypted RTSP URL"""
        feed_data = {
            "name": "Integration Test Camera",
            "feed_type": "FIXED_CAMERA",
            "rtsp_url": "rtsp://admin:password123@192.168.1.100:554/stream1",
            "location_name": "Main Gate",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "ai_enabled": True,
        }

        response = await client.post(
            "/api/v1/feeds",
            json=feed_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Integration Test Camera"
        assert data["feed_type"] == "FIXED_CAMERA"
        assert data["rtsp_url"] == "[ENCRYPTED]"  # Admin sees encrypted indicator
        assert data["ai_enabled"] is True

        # Verify URL is encrypted in database
        feed_repo = VideoFeedRepository(db_session)
        feed = await feed_repo.get(data["id"])
        assert feed is not None
        assert "rtsp://" not in feed.rtsp_url_encrypted
        assert "password123" not in feed.rtsp_url_encrypted

        # Verify decryption works
        decrypted = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
        assert decrypted == "rtsp://admin:password123@192.168.1.100:554/stream1"

    @pytest.mark.asyncio
    async def test_list_feeds_with_type_filter(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession
    ):
        """Test list feeds with feed type filtering"""
        # Create multiple feeds
        feed_service = FeedService(db_session)
        await feed_service.create_feed(
            name="Camera 1",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.101:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )
        await feed_service.create_feed(
            name="Drone 1",
            feed_type=FeedType.DRONE,
            rtsp_url="rtsp://admin:pass@192.168.1.102:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        # Filter by FIXED_CAMERA
        response = await client.get(
            "/api/v1/feeds?feed_type=FIXED_CAMERA",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for feed in data["feeds"]:
            assert feed["feed_type"] == "FIXED_CAMERA"

    @pytest.mark.asyncio
    async def test_list_feeds_with_zone_filter(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, test_zone: SecurityZone
    ):
        """Test list feeds with zone filtering"""
        # Create feed in zone
        feed_service = FeedService(db_session)
        await feed_service.create_feed(
            name="Zone Camera",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.103:554/stream",
            zone_id=test_zone.id,
            created_by=uuid4(),
        )

        # Filter by zone
        response = await client.get(
            f"/api/v1/feeds?zone_id={test_zone.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for feed in data["feeds"]:
            assert feed["zone_id"] == str(test_zone.id)

    @pytest.mark.asyncio
    async def test_list_feeds_with_status_filter(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession
    ):
        """Test list feeds with status filtering"""
        # Create feed
        feed_service = FeedService(db_session)
        await feed_service.create_feed(
            name="Offline Camera",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.104:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        # Filter by OFFLINE status
        response = await client.get(
            "/api/v1/feeds?status=OFFLINE",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for feed in data["feeds"]:
            assert feed["status"] == "OFFLINE"

    @pytest.mark.asyncio
    async def test_get_feed_details(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession
    ):
        """Test get feed details"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="Detail Test Camera",
            feed_type=FeedType.BODY_CAM,
            rtsp_url="rtsp://admin:pass@192.168.1.105:554/stream",
            zone_id=None,
            location_name="Building A",
            created_by=uuid4(),
        )

        # Get feed details
        response = await client.get(
            f"/api/v1/feeds/{feed.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(feed.id)
        assert data["name"] == "Detail Test Camera"
        assert data["feed_type"] == "BODY_CAM"
        assert data["location_name"] == "Building A"
        assert data["rtsp_url"] == "rtsp://***:***@***:***/**"  # Operator sees masked URL

    @pytest.mark.asyncio
    async def test_update_feed_basic_fields(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test update feed basic fields"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="Original Name",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.106:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        # Update feed
        update_data = {
            "name": "Updated Name",
            "location_name": "New Location",
            "latitude": 28.7041,
            "longitude": 77.1025,
        }

        response = await client.put(
            f"/api/v1/feeds/{feed.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["location_name"] == "New Location"
        assert data["latitude"] == 28.7041
        assert data["longitude"] == 77.1025

    @pytest.mark.asyncio
    async def test_update_feed_rtsp_url_reencryption(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test update feed with RTSP URL re-encryption"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="URL Update Test",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:oldpass@192.168.1.107:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        old_encrypted_url = feed.rtsp_url_encrypted

        # Update RTSP URL
        update_data = {
            "rtsp_url": "rtsp://admin:newpass@192.168.1.108:554/newstream",
        }

        response = await client.put(
            f"/api/v1/feeds/{feed.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200

        # Verify URL was re-encrypted
        feed_repo = VideoFeedRepository(db_session)
        updated_feed = await feed_repo.get(feed.id)
        assert updated_feed.rtsp_url_encrypted != old_encrypted_url

        # Verify new URL decrypts correctly
        decrypted = decrypt_rtsp_url(updated_feed.rtsp_url_encrypted, settings.encryption_master_key)
        assert decrypted == "rtsp://admin:newpass@192.168.1.108:554/newstream"

    @pytest.mark.asyncio
    async def test_delete_feed_soft_delete(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test delete feed (soft delete)"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="Delete Test Camera",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.109:554/stream",
            zone_id=None,
            ai_enabled=True,
            created_by=uuid4(),
        )

        # Delete feed
        response = await client.delete(
            f"/api/v1/feeds/{feed.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 204

        # Verify soft delete (status = MAINTENANCE, ai_enabled = False)
        feed_repo = VideoFeedRepository(db_session)
        deleted_feed = await feed_repo.get(feed.id)
        assert deleted_feed is not None  # Still exists
        assert deleted_feed.status == FeedStatus.MAINTENANCE.value
        assert deleted_feed.ai_enabled is False

    @pytest.mark.asyncio
    async def test_toggle_ai_processing(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, admin_user: User
    ):
        """Test toggle AI processing"""
        # Create feed with AI enabled
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="AI Toggle Test",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:pass@192.168.1.110:554/stream",
            zone_id=None,
            ai_enabled=True,
            created_by=admin_user.id,
        )

        assert feed.ai_enabled is True

        # Toggle AI off
        response = await client.post(
            f"/api/v1/feeds/{feed.id}/toggle-ai",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ai_enabled"] is False

        # Verify audit log entry created
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(
            filters=[],
            limit=1,
        )
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.action == "FEED_AI_TOGGLED"
        assert latest_log.resource_type == "VIDEO_FEED"


class TestRTSPURLEncryption:
    """Tests for RTSP URL encryption/decryption (Property 2)"""

    def test_encryption_round_trip(self):
        """
        **Validates: Requirements 2.2**
        
        Property 2: RTSP URL Encryption Round-Trip
        
        Verify round-trip encryption for various RTSP URLs
        """
        test_urls = [
            "rtsp://admin:password@192.168.1.100:554/stream1",
            "rtsp://user:pass123@camera.local:8554/live/main",
            "rtsp://10.0.0.50:554/h264",
            "rtsp://admin:p@ssw0rd!@192.168.1.200:554/stream/channel/1",
            "rtsp://camera1.example.com/video",
        ]

        for url in test_urls:
            # Encrypt
            encrypted = encrypt_rtsp_url(url, settings.encryption_master_key)

            # Verify encrypted is different from original
            assert encrypted != url
            assert "rtsp://" not in encrypted

            # Decrypt
            decrypted = decrypt_rtsp_url(encrypted, settings.encryption_master_key)

            # Verify round-trip
            assert decrypted == url, f"Round-trip failed for URL: {url}"

    def test_different_ciphertexts_for_same_plaintext(self):
        """
        **Validates: Requirements 2.2**
        
        Verify different ciphertexts for same plaintext (nonce randomization)
        """
        url = "rtsp://admin:password@192.168.1.100:554/stream"

        # Encrypt same URL multiple times
        encrypted1 = encrypt_rtsp_url(url, settings.encryption_master_key)
        encrypted2 = encrypt_rtsp_url(url, settings.encryption_master_key)
        encrypted3 = encrypt_rtsp_url(url, settings.encryption_master_key)

        # Verify different ciphertexts (due to random nonce)
        assert encrypted1 != encrypted2
        assert encrypted2 != encrypted3
        assert encrypted1 != encrypted3

        # Verify all decrypt to same plaintext
        assert decrypt_rtsp_url(encrypted1, settings.encryption_master_key) == url
        assert decrypt_rtsp_url(encrypted2, settings.encryption_master_key) == url
        assert decrypt_rtsp_url(encrypted3, settings.encryption_master_key) == url

    def test_decryption_with_wrong_key_fails(self):
        """
        **Validates: Requirements 2.2**
        
        Verify decryption with wrong key fails
        """
        url = "rtsp://admin:password@192.168.1.100:554/stream"
        encrypted = encrypt_rtsp_url(url, settings.encryption_master_key)

        # Try to decrypt with wrong key
        wrong_key = "0" * 64  # Different key

        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_rtsp_url(encrypted, wrong_key)


class TestFeedConnectionTesting:
    """Tests for feed connection testing"""

    @pytest.mark.asyncio
    async def test_connection_test_endpoint(
        self, client: AsyncClient, admin_token: str
    ):
        """Test connection test endpoint"""
        test_data = {
            "rtsp_url": "rtsp://invalid.host.test:554/stream",
            "timeout": 2,
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
        assert "metadata" in data
        # Invalid host should fail
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_connection_test_timeout_handling(
        self, db_session: AsyncSession
    ):
        """Test connection test timeout handling"""
        feed_service = FeedService(db_session)

        # Test with very short timeout
        result = await feed_service.test_connection(
            rtsp_url="rtsp://192.168.255.255:554/stream",  # Non-routable IP
            timeout=1,
        )

        assert result["success"] is False
        assert "timeout" in result["message"].lower() or "error" in result["message"].lower()
        assert result["metadata"] is None


class TestRTSPURLMasking:
    """Tests for RTSP URL masking"""

    @pytest.mark.asyncio
    async def test_admin_sees_encrypted_indicator(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test admin sees [ENCRYPTED] indicator"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="Masking Test Admin",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:secret@192.168.1.111:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        # Get feed as admin
        response = await client.get(
            f"/api/v1/feeds/{feed.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rtsp_url"] == "[ENCRYPTED]"

    @pytest.mark.asyncio
    async def test_non_admin_sees_masked_url(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession
    ):
        """Test non-admin sees rtsp://***:***@***:***/**"""
        # Create feed
        feed_service = FeedService(db_session)
        feed = await feed_service.create_feed(
            name="Masking Test Operator",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="rtsp://admin:secret@192.168.1.112:554/stream",
            zone_id=None,
            created_by=uuid4(),
        )

        # Get feed as operator
        response = await client.get(
            f"/api/v1/feeds/{feed.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rtsp_url"] == "rtsp://***:***@***:***/**"
