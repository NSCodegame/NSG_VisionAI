"""
Tests for Phase 9: Object Detection

Covers YOLOv8 worker, DetectionService, and Celery tasks.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.ml.detection.yolo_worker import ObjectDetectionWorker
from app.models.detection_event import DetectionType
from app.services.detection_service import DetectionService
from app.tasks.detection_tasks import process_frame_task

@pytest.fixture
def mock_yolo():
    with patch("app.ml.detection.yolo_worker.YOLO") as mock:
        model_instance = MagicMock()
        mock.return_value = model_instance
        
        # Mock result
        result = MagicMock()
        box = MagicMock()
        box.cls = [0] # Person class
        box.conf = [0.95]
        box.xyxy = [[10, 20, 110, 120]]
        result.boxes = [box]
        result.names = {0: "person"}
        model_instance.predict.return_value = [result]
        
        yield model_instance

@pytest.fixture
def mock_minio():
    with patch("app.services.detection_service.minio_client") as mock:
        mock.upload_bytes.return_value = True
        yield mock

@pytest.mark.asyncio
async def test_yolo_worker_inference(mock_yolo):
    """Test standard object detection inference."""
    worker = ObjectDetectionWorker(model_path="dummy.pt")
    frame = MagicMock()
    frame.shape = (480, 640, 3)
    
    detections = worker.process_frame(frame)
    
    assert len(detections) == 1
    assert detections[0]["object_class"] == "person"
    assert detections[0]["detection_type"] == DetectionType.OBJECT
    assert detections[0]["confidence"] == pytest.approx(0.95)
    
    # Check normalization
    box = detections[0]["bounding_box"]
    assert box["x"] == pytest.approx(10/640)
    assert box["y"] == pytest.approx(20/480)

@pytest.mark.asyncio
async def test_detection_service_persistence(mock_minio):
    """Test that DetectionService correctly interacts with DB and MinIO."""
    mock_session = MagicMock()
    service = DetectionService(mock_session)
    
    feed_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    det_data = {
        "detection_type": DetectionType.OBJECT,
        "confidence": 0.95,
        "bounding_box": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2},
        "object_class": "person"
    }
    
    with patch.object(service.detection_repo, "create") as mock_create:
        event = await service.create_detection_event(feed_id, timestamp, det_data, b"fake_frame")
        
        mock_create.assert_called_once()
        mock_minio.upload_bytes.assert_called_once()
        mock_session.commit.assert_called_once()

def test_process_frame_task(mock_yolo):
    """Test the Celery task glue."""
    feed_id = uuid4()
    timestamp_ms = 1713700000000
    frame_b64 = "ZmFrZV9mcmFtZQ==" # base64 for "fake_frame"
    
    with patch("app.tasks.detection_tasks.get_yolo_worker") as mock_get_worker:
        worker_instance = MagicMock()
        worker_instance.process_frame.return_value = [{"object_class": "person"}]
        mock_get_worker.return_value = worker_instance
        
        with patch("app.tasks.detection_tasks.DetectionService") as mock_service_class:
            service_instance = MagicMock()
            mock_service_class.return_value = service_instance
            
            # Since process_frame_task is a Celery task, we call it directly for the unit test
            process_frame_task(str(feed_id), frame_b64, timestamp_ms)
            
            worker_instance.process_frame.assert_called_once()
