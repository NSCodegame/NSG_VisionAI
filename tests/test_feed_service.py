"""Tests for Video Feed Service"""
import pytest
from uuid import uuid4

from app.models.video_feed import FeedType, FeedStatus
from app.services.feed_service import FeedService
from app.utils.encryption import decrypt_rtsp_url, encrypt_rtsp_url
from app.core.config import settings


@pytest.mark.asyncio
async def test_create_feed(db_session):
    """Test creating a video feed with encrypted RTSP URL"""
    service = FeedService(db_session)
    
    # Create feed
    feed = await service.create_feed(
        name="Test Camera 1",
        feed_type=FeedType.FIXED_CAMERA,
        rtsp_url="rtsp://admin:password@192.168.1.100:554/stream1",
        zone_id=None,
        location_name="Main Gate",
        latitude=28.6139,
        longitude=77.2090,
        ai_enabled=True,
        created_by=uuid4(),
        ip_address="192.168.1.50",
    )
    
    assert feed is not None
    assert feed.name == "Test Camera 1"
    assert feed.feed_type == FeedType.FIXED_CAMERA.value
    assert feed.status == FeedStatus.OFFLINE.value
    assert feed.ai_enabled is True
    assert feed.rtsp_url_encrypted is not None
    
    # Verify URL is encrypted (not plain text)
    assert "rtsp://" not in feed.rtsp_url_encrypted
    assert "password" not in feed.rtsp_url_encrypted
    
    # Verify decryption works
    decrypted_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
    assert decrypted_url == "rtsp://admin:password@192.168.1.100:554/stream1"


@pytest.mark.asyncio
async def test_update_feed(db_session):
    """Test updating feed details"""
    service = FeedService(db_session)
    
    # Create feed
    feed = await service.create_feed(
        name="Test Camera 2",
        feed_type=FeedType.DRONE,
        rtsp_url="rtsp://admin:pass@192.168.1.101:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    # Update feed
    updated_feed = await service.update_feed(
        feed_id=feed.id,
        name="Updated Camera 2",
        location_name="Perimeter North",
        updated_by=uuid4(),
    )
    
    assert updated_feed is not None
    assert updated_feed.name == "Updated Camera 2"
    assert updated_feed.location_name == "Perimeter North"


@pytest.mark.asyncio
async def test_update_feed_with_new_rtsp_url(db_session):
    """Test updating feed with new RTSP URL (re-encryption)"""
    service = FeedService(db_session)
    
    # Create feed
    feed = await service.create_feed(
        name="Test Camera 3",
        feed_type=FeedType.BODY_CAM,
        rtsp_url="rtsp://user:pass1@192.168.1.102:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    old_encrypted_url = feed.rtsp_url_encrypted
    
    # Update with new RTSP URL
    updated_feed = await service.update_feed(
        feed_id=feed.id,
        rtsp_url="rtsp://user:pass2@192.168.1.103:554/newstream",
        updated_by=uuid4(),
    )
    
    assert updated_feed is not None
    assert updated_feed.rtsp_url_encrypted != old_encrypted_url
    
    # Verify new URL is correctly encrypted
    decrypted_url = decrypt_rtsp_url(updated_feed.rtsp_url_encrypted, settings.encryption_master_key)
    assert decrypted_url == "rtsp://user:pass2@192.168.1.103:554/newstream"


@pytest.mark.asyncio
async def test_delete_feed(db_session):
    """Test soft deleting a feed"""
    service = FeedService(db_session)
    
    # Create feed
    feed = await service.create_feed(
        name="Test Camera 4",
        feed_type=FeedType.LEGACY_CCTV,
        rtsp_url="rtsp://admin:pass@192.168.1.104:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    # Delete feed
    deleted_feed = await service.delete_feed(
        feed_id=feed.id,
        deleted_by=uuid4(),
    )
    
    assert deleted_feed is not None
    assert deleted_feed.status == FeedStatus.MAINTENANCE.value
    assert deleted_feed.ai_enabled is False


@pytest.mark.asyncio
async def test_toggle_ai_processing(db_session):
    """Test toggling AI processing flag"""
    service = FeedService(db_session)
    
    # Create feed with AI enabled
    feed = await service.create_feed(
        name="Test Camera 5",
        feed_type=FeedType.FIXED_CAMERA,
        rtsp_url="rtsp://admin:pass@192.168.1.105:554/stream",
        zone_id=None,
        ai_enabled=True,
        created_by=uuid4(),
    )
    
    assert feed.ai_enabled is True
    
    # Toggle AI off
    toggled_feed = await service.toggle_ai_processing(
        feed_id=feed.id,
        toggled_by=uuid4(),
    )
    
    assert toggled_feed is not None
    assert toggled_feed.ai_enabled is False
    
    # Toggle AI back on
    toggled_feed = await service.toggle_ai_processing(
        feed_id=feed.id,
        toggled_by=uuid4(),
    )
    
    assert toggled_feed.ai_enabled is True


@pytest.mark.asyncio
async def test_get_feeds_with_filters(db_session):
    """Test getting feeds with various filters"""
    service = FeedService(db_session)
    
    # Create multiple feeds
    await service.create_feed(
        name="Camera 1",
        feed_type=FeedType.FIXED_CAMERA,
        rtsp_url="rtsp://admin:pass@192.168.1.106:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    await service.create_feed(
        name="Drone 1",
        feed_type=FeedType.DRONE,
        rtsp_url="rtsp://admin:pass@192.168.1.107:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    await service.create_feed(
        name="Camera 2",
        feed_type=FeedType.FIXED_CAMERA,
        rtsp_url="rtsp://admin:pass@192.168.1.108:554/stream",
        zone_id=None,
        created_by=uuid4(),
    )
    
    # Get all feeds
    all_feeds = await service.get_feeds()
    assert len(all_feeds) >= 3
    
    # Filter by feed type
    camera_feeds = await service.get_feeds(feed_type=FeedType.FIXED_CAMERA)
    assert len(camera_feeds) >= 2
    assert all(f.feed_type == FeedType.FIXED_CAMERA.value for f in camera_feeds)
    
    drone_feeds = await service.get_feeds(feed_type=FeedType.DRONE)
    assert len(drone_feeds) >= 1
    assert all(f.feed_type == FeedType.DRONE.value for f in drone_feeds)
    
    # Filter by status
    offline_feeds = await service.get_feeds(status=FeedStatus.OFFLINE)
    assert len(offline_feeds) >= 3


@pytest.mark.asyncio
async def test_invalid_rtsp_url(db_session):
    """Test that invalid RTSP URLs are rejected"""
    service = FeedService(db_session)
    
    with pytest.raises(ValueError, match="Invalid RTSP URL format"):
        await service.create_feed(
            name="Invalid Feed",
            feed_type=FeedType.FIXED_CAMERA,
            rtsp_url="http://invalid.com/stream",  # Not RTSP
            zone_id=None,
            created_by=uuid4(),
        )


@pytest.mark.asyncio
async def test_test_connection_invalid_url(db_session):
    """Test connection testing with invalid URL"""
    service = FeedService(db_session)
    
    # Test with invalid RTSP URL (will timeout or fail)
    result = await service.test_connection(
        rtsp_url="rtsp://invalid.host.test:554/stream",
        timeout=2,  # Short timeout for test
    )
    
    assert result["success"] is False
    assert result["message"] != ""
    assert result["metadata"] is None


def test_rtsp_url_encryption_round_trip():
    """
    **Validates: Requirements 2.2**
    
    Property 2: RTSP URL Encryption Round-Trip
    
    For any valid RTSP URL string, encrypting the URL using AES-256-GCM
    and then decrypting it SHALL produce a string equivalent to the original URL.
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
