"""
Tests for Phase 11: Person Tracking

Covers PersonTrackingWorker, TrackedPersonService, and trajectory management.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from app.ml.tracking.bytetrack_worker import PersonTrackingWorker
from app.models.tracked_person import OperatorLabel
from app.services.tracked_person_service import TrackedPersonService

@pytest.fixture
def mock_yolo_track():
    with patch("app.ml.tracking.bytetrack_worker.YOLO") as mock:
        model_instance = MagicMock()
        mock.return_value = model_instance
        
        # Mock result
        result = MagicMock()
        box = MagicMock()
        box.cls = [0] # Person
        box.conf = [0.9]
        box.xyxy = [[10, 20, 110, 120]]
        
        # Mock tracking IDs
        result.boxes = box
        result.boxes.id = MagicMock()
        result.boxes.id.__iter__.return_value = [MagicMock(item=lambda: 1)]
        result.boxes.__iter__.return_value = [box]
        
        result.names = {0: "person"}
        model_instance.track.return_value = [result]
        
        yield model_instance

@pytest.mark.asyncio
async def test_tracking_worker_update(mock_yolo_track):
    """Test tracking ID assignment and bounding box normalization."""
    worker = PersonTrackingWorker(model_path="dummy.pt")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    tracks = worker.update_tracks(frame)
    
    assert len(tracks) == 1
    assert tracks[0]["track_id"] == 1
    assert tracks[0]["object_class"] == "person"
    assert tracks[0]["bounding_box"]["x"] == pytest.approx(10/640)

@pytest.mark.asyncio
async def test_tracked_person_service_lifecycle():
    """Test creating a new track and appending trajectory points."""
    mock_session = MagicMock()
    service = TrackedPersonService(mock_session)
    
    feed_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    track_data = {
        "track_id": 1,
        "bounding_box": {"x": 0.5, "y": 0.5},
        "object_class": "person",
        "confidence": 0.9
    }
    
    # 1. Test creation of NEW track
    with patch.object(service.person_repo, "get_by_track_id", return_value=None):
        with patch.object(service.person_repo, "create") as mock_create:
            mock_create.return_value = MagicMock()
            
            await service.update_person_track(feed_id, track_data, timestamp)
            
            mock_create.assert_called_once()
            kwargs = mock_create.call_args[1]
            assert kwargs["track_id"] == "1"
            assert kwargs["trajectory"]["points"][0]["position"]["x"] == 0.5

    # 2. Test update of EXISTING track
    existing_person = MagicMock()
    existing_person.id = uuid4()
    existing_person.feed_ids_seen = {"ids": []}
    
    with patch.object(service.person_repo, "get_by_track_id", return_value=existing_person):
        with patch.object(service.person_repo, "update_trajectory") as mock_update_traj:
            await service.update_person_track(feed_id, track_data, timestamp)
            
            mock_update_traj.assert_called_once_with(existing_person.id, pytest.any)
            assert str(feed_id) in existing_person.feed_ids_seen["ids"]
