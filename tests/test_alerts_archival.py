"""
Tests for Phase 13 & 14: Alert Engine and Video Archival

Covers AlertService deduplication and ArchivalService encryption/storage logic.
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.models.alert import AlertPriority, AlertStatus, AlertType
from app.models.detection_event import DetectionType
from app.services.alert_service import AlertService
from app.services.archival_service import ArchivalService
from app.utils.encryption import decrypt_binary_aes_gcm

@pytest.fixture
def mock_minio():
    with patch("app.services.archival_service.minio_client") as mock:
        mock.upload_bytes.return_value = True
        yield mock

@pytest.mark.asyncio
async def test_alert_deduplication():
    """Test that multiple detections within 30s only trigger one alert update."""
    mock_session = MagicMock()
    service = AlertService(mock_session)
    
    feed_id = uuid4()
    event_id = uuid4()
    
    # 1. Mock existing alert found
    existing_alert = MagicMock()
    existing_alert.id = uuid4()
    
    with patch.object(service.alert_repo, "find_duplicate", return_value=existing_alert):
        with patch.object(service.alert_repo, "increment_occurrence") as mock_inc:
            await service.process_detection(
                event_id=event_id,
                feed_id=feed_id,
                detection_type=DetectionType.FACE,
                confidence=0.95
            )
            mock_inc.assert_called_once_with(existing_alert.id)

@pytest.mark.asyncio
async def test_alert_prioritization():
    """Test priority calculation logic for weapon detections."""
    mock_session = MagicMock()
    service = AlertService(mock_session)
    
    with patch.object(service.alert_repo, "find_duplicate", return_value=None):
        with patch.object(service.alert_repo, "create") as mock_create:
            await service.process_detection(
                event_id=uuid4(),
                feed_id=uuid4(),
                detection_type=DetectionType.OBJECT,
                confidence=0.99,
                object_class="pistol"
            )
            
            kwargs = mock_create.call_args[1]
            assert kwargs["priority"] == "P1_CRITICAL"
            assert kwargs["alert_type"] == AlertType.WEAPON_DETECTED.value

@pytest.mark.asyncio
async def test_archival_encryption_cycle(mock_minio):
    """Test that archived video is correctly encrypted and metadata is stored."""
    mock_session = MagicMock()
    service = ArchivalService(mock_session)
    
    feed_id = uuid4()
    raw_data = b"fake-video-segment-data"
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=10)
    
    with patch.object(service.segment_repo, "create") as mock_create:
        mock_create.return_value = MagicMock()
        
        await service.archive_video_segment(
            feed_id=feed_id,
            start_time=start_time,
            end_time=end_time,
            raw_video_bytes=raw_data
        )
        
        # Verify encryption and upload
        mock_minio.upload_bytes.assert_called()
        encrypted_payload = mock_minio.upload_bytes.call_args[0][0]
        
        # Verify we can decrypt it back
        from app.core.config import settings
        decrypted = decrypt_binary_aes_gcm(encrypted_payload, settings.encryption_master_key)
        assert decrypted == raw_data
        
        mock_create.assert_called_once()
        kwargs = mock_create.call_args[1]
        assert kwargs["feed_id"] == feed_id
        assert "archive/" in kwargs["storage_path"]
