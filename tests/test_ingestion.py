"""
Tests for Phase 8: Video Ingestion

Covers RTSP and WebRTC ingesters and the IngesterService lifecycle management.
"""

import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.ml.ingestion.stream_ingester import VideoStreamIngester
from app.models.video_feed import FeedStatus, FeedType
from app.services.ingester_service import IngesterService

@pytest.fixture
def mock_redis():
    with patch("app.core.redis.get_redis") as mock:
        redis_instance = MagicMock()
        mock.return_value = redis_instance
        yield redis_instance

@pytest.fixture
def mock_cap():
    with patch("cv2.VideoCapture") as mock:
        cap_instance = MagicMock()
        cap_instance.isOpened.return_value = True
        cap_instance.read.return_value = (True, MagicMock())
        mock.return_value = cap_instance
        yield cap_instance

@pytest.mark.asyncio
async def test_rtsp_ingester_connection_success(mock_cap, mock_redis):
    """Test that the RTSP ingester can successfully connect and read frames."""
    ingester = VideoStreamIngester()
    feed_id = str(uuid4())
    rtsp_url = "rtsp://test:test@127.0.0.1/live"

    # Patch database status update to avoid real DB dependency in unit test
    with patch.object(ingester, "_update_feed_status") as mock_status:
        # Start ingestion
        await ingester.connect_stream(feed_id, rtsp_url)
        
        # Give it a tiny bit of time to run the loop
        await asyncio.sleep(0.5)
        
        # Verify health
        health = await ingester.get_stream_health(feed_id)
        assert health == "CONNECTED"
        
        # Verify status update called
        mock_status.assert_called_with(feed_id, "ACTIVE")
        
        # Stop
        await ingester.disconnect_stream(feed_id)
        assert feed_id not in ingester._streams

@pytest.mark.asyncio
async def test_ingester_service_start_active_feeds(mock_cap, mock_redis):
    """Test that IngesterService starts all feeds marked as ACTIVE."""
    mock_session = MagicMock()
    service = IngesterService(mock_session)
    
    feed1 = MagicMock(id=uuid4(), feed_type=FeedType.FIXED_CAMERA.value, status=FeedStatus.ACTIVE.value, rtsp_url_encrypted="enc1")
    
    with patch.object(service.feed_repo, "get_multi", return_value=[feed1]), \
         patch("app.services.ingester_service.decrypt_rtsp_url", return_value="rtsp://url1"), \
         patch("app.ml.ingestion.stream_ingester.ingester.connect_stream") as mock_connect:
        
        count = await service.start_all_active_feeds()
        assert count == 1
        mock_connect.assert_called_once()
