"""
Integration tests for security zone functionality
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.security import hash_password
from app.models.alert import Alert, AlertStatus, AlertType, Priority
from app.models.security_zone import SecurityZone, ThreatLevel, ZoneType
from app.models.user import User, UserRole
from app.models.video_feed import FeedType, VideoFeed
from app.repositories.alert import AlertRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.security_zone import SecurityZoneRepository
from app.repositories.user import UserRepository
from app.repositories.video_feed import VideoFeedRepository
from app.services.auth_service import AuthService
from app.services.zone_service import ZoneService
from app.utils.encryption import encrypt_rtsp_url
from app.core.config import settings


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing"""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        service_number="NSG/ADMIN/ZONE1",
        full_name="Zone Test Admin",
        role=UserRole.ADMIN.value,
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    await db_session.commit()
    return user


@pytest.fixture
async def commander_user(db_session: AsyncSession) -> User:
    """Create commander user for testing"""
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        service_number="NSG/CMD/ZONE1",
        full_name="Zone Test Commander",
        role=UserRole.COMMANDER.value,
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
        service_number="NSG/OP/ZONE1",
        full_name="Zone Test Operator",
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
        service_number="NSG/ADMIN/ZONE1",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def commander_token(db_session: AsyncSession, commander_user: User) -> str:
    """Generate commander access token"""
    auth_service = AuthService(db_session)
    _, tokens = await auth_service.authenticate_user(
        service_number="NSG/CMD/ZONE1",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
async def operator_token(db_session: AsyncSession, operator_user: User) -> str:
    """Generate operator access token"""
    auth_service = AuthService(db_session)
    _, tokens = await auth_service.authenticate_user(
        service_number="NSG/OP/ZONE1",
        password="TestPassword123!",
    )
    return tokens["access_token"]


@pytest.fixture
def valid_polygon():
    """Valid polygon coordinates for testing"""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                {"lat": 28.6139, "lng": 77.2090},
                {"lat": 28.6140, "lng": 77.2091},
                {"lat": 28.6141, "lng": 77.2089},
                {"lat": 28.6139, "lng": 77.2090},  # Closed polygon
            ]
        ],
    }


class TestZoneCRUDOperations:
    """Integration tests for zone CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_zone_with_valid_polygon(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test create zone with valid polygon coordinates"""
        zone_data = {
            "name": "Test Perimeter Zone",
            "zone_type": "PERIMETER",
            "polygon_coordinates": valid_polygon,
            "threat_level": "GREEN",
        }

        response = await client.post(
            "/api/v1/zones",
            json=zone_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Perimeter Zone"
        assert data["zone_type"] == "PERIMETER"
        assert data["threat_level"] == "GREEN"
        assert data["polygon_coordinates"] == valid_polygon

        # Verify audit log entry created
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(filters=[], limit=1)
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.action == "ZONE_CREATED"
        assert latest_log.resource_type == "SECURITY_ZONE"

    @pytest.mark.asyncio
    async def test_create_zone_invalid_polygon_not_closed(
        self, client: AsyncClient, admin_token: str
    ):
        """Test create zone with invalid polygon (not closed)"""
        zone_data = {
            "name": "Invalid Zone",
            "zone_type": "RESTRICTED",
            "polygon_coordinates": {
                "type": "Polygon",
                "coordinates": [
                    [
                        {"lat": 28.6139, "lng": 77.2090},
                        {"lat": 28.6140, "lng": 77.2091},
                        {"lat": 28.6141, "lng": 77.2089},
                        # Missing closing point
                    ]
                ],
            },
            "threat_level": "GREEN",
        }

        response = await client.post(
            "/api/v1/zones",
            json=zone_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "Invalid polygon coordinates" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_zone_invalid_polygon_too_few_points(
        self, client: AsyncClient, admin_token: str
    ):
        """Test create zone with invalid polygon (too few points)"""
        zone_data = {
            "name": "Invalid Zone",
            "zone_type": "PUBLIC",
            "polygon_coordinates": {
                "type": "Polygon",
                "coordinates": [
                    [
                        {"lat": 28.6139, "lng": 77.2090},
                        {"lat": 28.6140, "lng": 77.2091},
                        {"lat": 28.6139, "lng": 77.2090},  # Only 2 unique points
                    ]
                ],
            },
            "threat_level": "GREEN",
        }

        response = await client.post(
            "/api/v1/zones",
            json=zone_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "Invalid polygon coordinates" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_zones_with_type_filter(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test list zones with zone type filtering"""
        # Create multiple zones
        zone_service = ZoneService(db_session)
        await zone_service.create_zone(
            name="Perimeter Zone 1",
            zone_type=ZoneType.PERIMETER,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )
        await zone_service.create_zone(
            name="Restricted Zone 1",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.AMBER,
        )

        # Filter by PERIMETER
        response = await client.get(
            "/api/v1/zones?zone_type=PERIMETER",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for zone in data["zones"]:
            assert zone["zone_type"] == "PERIMETER"

    @pytest.mark.asyncio
    async def test_list_zones_with_threat_level_filter(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test list zones with threat level filtering"""
        # Create zones with different threat levels
        zone_service = ZoneService(db_session)
        await zone_service.create_zone(
            name="Green Zone",
            zone_type=ZoneType.PUBLIC,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )
        await zone_service.create_zone(
            name="Red Zone",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.RED,
        )

        # Filter by RED threat level
        response = await client.get(
            "/api/v1/zones?threat_level=RED",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for zone in data["zones"]:
            assert zone["threat_level"] == "RED"

    @pytest.mark.asyncio
    async def test_get_zone_details(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test get zone details"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Detail Test Zone",
            zone_type=ZoneType.INNER_CORDON,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.AMBER,
        )

        # Get zone details
        response = await client.get(
            f"/api/v1/zones/{zone.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(zone.id)
        assert data["name"] == "Detail Test Zone"
        assert data["zone_type"] == "INNER_CORDON"
        assert data["threat_level"] == "AMBER"
        assert data["polygon_coordinates"] == valid_polygon

    @pytest.mark.asyncio
    async def test_get_zone_not_found(
        self, client: AsyncClient, operator_token: str
    ):
        """Test get non-existent zone"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/zones/{fake_uuid}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_zone_basic_fields(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update zone basic fields"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Original Name",
            zone_type=ZoneType.PERIMETER,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Update zone
        update_data = {
            "name": "Updated Name",
            "zone_type": "RESTRICTED",
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["zone_type"] == "RESTRICTED"

        # Verify audit log entry created
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(filters=[], limit=1)
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.action == "ZONE_UPDATED"

    @pytest.mark.asyncio
    async def test_update_zone_polygon_coordinates(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update zone polygon coordinates"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Polygon Update Test",
            zone_type=ZoneType.PUBLIC,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # New polygon
        new_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    {"lat": 28.7041, "lng": 77.1025},
                    {"lat": 28.7042, "lng": 77.1026},
                    {"lat": 28.7043, "lng": 77.1024},
                    {"lat": 28.7041, "lng": 77.1025},
                ]
            ],
        }

        # Update polygon
        update_data = {"polygon_coordinates": new_polygon}

        response = await client.put(
            f"/api/v1/zones/{zone.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["polygon_coordinates"] == new_polygon

    @pytest.mark.asyncio
    async def test_update_zone_invalid_polygon(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update zone with invalid polygon"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Invalid Update Test",
            zone_type=ZoneType.PERIMETER,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Invalid polygon (not closed)
        invalid_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    {"lat": 28.7041, "lng": 77.1025},
                    {"lat": 28.7042, "lng": 77.1026},
                    {"lat": 28.7043, "lng": 77.1024},
                    # Missing closing point
                ]
            ],
        }

        # Update with invalid polygon
        update_data = {"polygon_coordinates": invalid_polygon}

        response = await client.put(
            f"/api/v1/zones/{zone.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "Invalid polygon coordinates" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_zone_without_dependencies(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test delete zone without dependencies"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Delete Test Zone",
            zone_type=ZoneType.PUBLIC,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Delete zone
        response = await client.delete(
            f"/api/v1/zones/{zone.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 204

        # Verify zone is deleted
        zone_repo = SecurityZoneRepository(db_session)
        deleted_zone = await zone_repo.get(zone.id)
        assert deleted_zone is None

        # Verify audit log entry created
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(filters=[], limit=1)
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.action == "ZONE_DELETED"

    @pytest.mark.asyncio
    async def test_delete_zone_with_active_feeds_fails(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test delete zone with active feeds (should fail)"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Zone With Feeds",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.AMBER,
        )

        # Create feed in zone
        feed_repo = VideoFeedRepository(db_session)
        encrypted_url = encrypt_rtsp_url(
            "rtsp://admin:pass@192.168.1.200:554/stream",
            settings.encryption_master_key,
        )
        await feed_repo.create(
            name="Zone Feed",
            feed_type=FeedType.FIXED_CAMERA.value,
            rtsp_url_encrypted=encrypted_url,
            zone_id=zone.id,
            status="OFFLINE",
            ai_enabled=True,
        )
        await db_session.commit()

        # Try to delete zone
        response = await client.delete(
            f"/api/v1/zones/{zone.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "Cannot delete zone" in response.json()["detail"]
        assert "video feeds" in response.json()["detail"]

        # Verify zone still exists
        zone_repo = SecurityZoneRepository(db_session)
        existing_zone = await zone_repo.get(zone.id)
        assert existing_zone is not None


class TestThreatLevelUpdates:
    """Tests for threat level updates with alert recalculation"""

    @pytest.mark.asyncio
    async def test_update_threat_level_basic(
        self, client: AsyncClient, commander_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update threat level"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Threat Level Test Zone",
            zone_type=ZoneType.PERIMETER,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Update threat level
        update_data = {
            "threat_level": "AMBER",
            "confirmation": False,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {commander_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zone"]["threat_level"] == "AMBER"
        assert "affected_alerts" in data

        # Verify audit log entry created
        audit_repo = AuditLogRepository(db_session)
        logs = await audit_repo.get_multi(filters=[], limit=1)
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.action == "ZONE_THREAT_LEVEL_UPDATED"

    @pytest.mark.asyncio
    async def test_update_threat_level_to_critical_without_confirmation_fails(
        self, client: AsyncClient, commander_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update threat level to CRITICAL without confirmation (should fail)"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Critical Test Zone",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Try to update to CRITICAL without confirmation
        update_data = {
            "threat_level": "CRITICAL",
            "confirmation": False,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {commander_token}"},
        )

        assert response.status_code == 400
        assert "Confirmation required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_threat_level_to_critical_with_confirmation(
        self, client: AsyncClient, commander_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test update threat level to CRITICAL with confirmation"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Critical Confirmed Zone",
            zone_type=ZoneType.INNER_CORDON,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.RED,
        )

        # Update to CRITICAL with confirmation
        update_data = {
            "threat_level": "CRITICAL",
            "confirmation": True,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {commander_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zone"]["threat_level"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_threat_level_update_recalculates_alert_priorities(
        self, client: AsyncClient, commander_token: str, db_session: AsyncSession, valid_polygon, admin_user: User
    ):
        """Test threat level update recalculates alert priorities"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Alert Recalc Zone",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
            created_by=admin_user.id,
        )

        # Create feed in zone
        feed_repo = VideoFeedRepository(db_session)
        encrypted_url = encrypt_rtsp_url(
            "rtsp://admin:pass@192.168.1.201:554/stream",
            settings.encryption_master_key,
        )
        feed = await feed_repo.create(
            name="Alert Test Feed",
            feed_type=FeedType.FIXED_CAMERA.value,
            rtsp_url_encrypted=encrypted_url,
            zone_id=zone.id,
            status="ACTIVE",
            ai_enabled=True,
        )
        await db_session.commit()

        # Create active alert in zone
        alert_repo = AlertRepository(db_session)
        alert = await alert_repo.create(
            detection_event_id=uuid4(),
            alert_type=AlertType.ZONE_BREACH.value,
            priority=Priority.P4_LOW.value,  # Low priority with GREEN threat level
            status=AlertStatus.ACTIVE.value,
            feed_id=feed.id,
            zone_id=zone.id,
            confidence_score=0.80,
        )
        await db_session.commit()

        # Update threat level to RED
        update_data = {
            "threat_level": "RED",
            "confirmation": False,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {commander_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zone"]["threat_level"] == "RED"
        assert data["affected_alerts"] >= 1  # At least one alert recalculated

        # Verify alert priority was recalculated
        updated_alert = await alert_repo.get(alert.id)
        # Priority should be higher now with RED threat level
        assert updated_alert.priority != Priority.P4_LOW.value


class TestZoneAccessControl:
    """Tests for zone access control"""

    @pytest.mark.asyncio
    async def test_operator_can_list_zones(
        self, client: AsyncClient, operator_token: str
    ):
        """Test operator can list zones"""
        response = await client.get(
            "/api/v1/zones",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_cannot_create_zone(
        self, client: AsyncClient, operator_token: str, valid_polygon
    ):
        """Test operator cannot create zone"""
        zone_data = {
            "name": "Unauthorized Zone",
            "zone_type": "PUBLIC",
            "polygon_coordinates": valid_polygon,
            "threat_level": "GREEN",
        }

        response = await client.post(
            "/api/v1/zones",
            json=zone_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_update_zone(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test operator cannot update zone"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Test Zone",
            zone_type=ZoneType.PUBLIC,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Try to update as operator
        update_data = {"name": "Updated Name"}

        response = await client.put(
            f"/api/v1/zones/{zone.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_delete_zone(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test operator cannot delete zone"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Test Zone",
            zone_type=ZoneType.PUBLIC,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Try to delete as operator
        response = await client.delete(
            f"/api/v1/zones/{zone.id}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_update_threat_level(
        self, client: AsyncClient, operator_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test operator cannot update threat level"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Test Zone",
            zone_type=ZoneType.RESTRICTED,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Try to update threat level as operator
        update_data = {
            "threat_level": "AMBER",
            "confirmation": False,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_commander_can_update_threat_level(
        self, client: AsyncClient, commander_token: str, db_session: AsyncSession, valid_polygon
    ):
        """Test commander can update threat level"""
        # Create zone
        zone_service = ZoneService(db_session)
        zone = await zone_service.create_zone(
            name="Commander Test Zone",
            zone_type=ZoneType.PERIMETER,
            polygon_coordinates=valid_polygon,
            threat_level=ThreatLevel.GREEN,
        )

        # Update threat level as commander
        update_data = {
            "threat_level": "RED",
            "confirmation": False,
        }

        response = await client.put(
            f"/api/v1/zones/{zone.id}/threat-level",
            json=update_data,
            headers={"Authorization": f"Bearer {commander_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_create_update_delete_zones(
        self, client: AsyncClient, admin_token: str, valid_polygon
    ):
        """Test admin has full zone management permissions"""
        # Create zone
        zone_data = {
            "name": "Admin Test Zone",
            "zone_type": "INNER_CORDON",
            "polygon_coordinates": valid_polygon,
            "threat_level": "AMBER",
        }

        create_response = await client.post(
            "/api/v1/zones",
            json=zone_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert create_response.status_code == 201
        zone_id = create_response.json()["id"]

        # Update zone
        update_data = {"name": "Updated Admin Zone"}

        update_response = await client.put(
            f"/api/v1/zones/{zone_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert update_response.status_code == 200

        # Delete zone
        delete_response = await client.delete(
            f"/api/v1/zones/{zone_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert delete_response.status_code == 204
