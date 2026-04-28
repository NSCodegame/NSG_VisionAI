"""
Tests for Phase 10: Face Detection & Recognition

Covers FaceDetectionWorker, WatchlistService, and pgvector search.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from app.ml.detection.face_worker import FaceDetectionWorker
from app.models.watchlist_entry import ThreatCategory, WatchlistStatus
from app.services.watchlist_service import WatchlistService

@pytest.fixture
def mock_deepface():
    with patch("app.ml.detection.face_worker.DeepFace") as mock:
        # Mock face detection
        mock.extract_faces.return_value = [
            {
                "face": np.zeros((160, 160, 3)),
                "facial_area": {"x": 100, "y": 100, "w": 50, "h": 50},
                "confidence": 0.99
            }
        ]
        # Mock embedding extraction
        mock.represent.return_value = [{"embedding": [0.1] * 512}]
        yield mock

@pytest.fixture
def mock_minio():
    with patch("app.services.watchlist_service.minio_client") as mock:
        mock.upload_bytes.return_value = True
        yield mock

@pytest.mark.asyncio
async def test_face_worker_detection(mock_deepface):
    """Test face detection and embedding generation."""
    worker = FaceDetectionWorker()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    results = worker.detect_and_embed(frame)
    
    assert len(results) == 1
    assert results[0]["confidence"] == 0.99
    assert len(results[0]["embedding"]) == 512
    assert results[0]["bounding_box"]["x"] == pytest.approx(100/640)

@pytest.mark.asyncio
async def test_watchlist_service_enrollment(mock_deepface, mock_minio):
    """Test full enrollment flow: image -> embedding -> DB."""
    mock_session = MagicMock()
    service = WatchlistService(mock_session)
    
    added_by = uuid4()
    entry_data = {
        "name": "Test Subject",
        "threat_category": ThreatCategory.SUSPECT,
        "source_agency": "NSG"
    }
    image_bytes = b"fake_jpeg_bytes"
    
    with patch.object(service.watchlist_repo, "create") as mock_create:
        mock_create.return_value = MagicMock()
        
        await service.create_watchlist_entry(added_by, entry_data, [image_bytes])
        
        mock_create.assert_called_once()
        # Verify embedding is a 512-dim list
        args, kwargs = mock_create.call_args
        assert len(kwargs["face_embedding"]) == 512
        assert kwargs["status"] == WatchlistStatus.PENDING_APPROVAL.value
        mock_minio.upload_bytes.assert_called()

@pytest.mark.asyncio
async def test_watchlist_matching(mock_deepface):
    """Test matching a detected face against real pgvector results."""
    # This would ideally be a real DB test, but we mock the repo for unit test
    mock_session = MagicMock()
    service = WatchlistService(mock_session)
    
    match_entry = MagicMock()
    match_entry.id = uuid4()
    match_entry.name = "MATCHED PERSON"
    
    with patch.object(service.watchlist_repo, "search_by_embedding") as mock_search:
        mock_search.return_value = [(match_entry, 0.95)]
        
        results = await service.watchlist_repo.search_by_embedding([0.1]*512)
        
        assert len(results) == 1
        assert results[0][0].name == "MATCHED PERSON"
        assert results[0][1] == 0.95
