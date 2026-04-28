"""
PersonTrackingWorker — Phase 11, Task 11.1

Coordinates multi-object tracking (MOT) across video frames using ByteTrack.
Maintains identity continuity and updates trajectories in the database.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from ultralytics import YOLO

from app.core.config import settings
from app.ml.tracking.reid_worker import get_reid_worker

logger = logging.getLogger(__name__)

class PersonTrackingWorker:
    """
    Worker for maintaining tracks of people and vehicles.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the tracker. 
        We use the YOLOv8 tracking capabilities which support ByteTrack.
        """
        self.model_path = model_path or str(settings.yolo_model_path)
        # We load the tracking configuration
        self.tracker_config = "bytetrack.yaml" 
        try:
            self.model = YOLO(self.model_path)
            logger.info("Tracking worker initialized with model %s", self.model_path)
        except Exception as e:
            logger.error("Failed to initialize tracking model: %s", e)
            self.model = None

    def update_tracks(self, frame: np.ndarray, persist: bool = True) -> List[Dict]:
        """
        Update tracks based on a new frame.
        
        Args:
            frame: Current video frame (BGR)
            persist: Whether to maintain tracks across calls
            
        Returns:
            List of active tracks with track_id and bounding box.
        """
        if self.model is None:
            return []

        # YOLOv8 track() method handles detection + tracking in one go
        # This is more efficient than separate steps if used on the same node
        results = self.model.track(
            source=frame,
            persist=persist,
            tracker=self.tracker_config,
            conf=settings.yolo_confidence_threshold,
            iou=settings.yolo_nms_threshold,
            imgsz=settings.yolo_input_size,
            verbose=False
        )

        tracks = []
        if not results:
            return tracks

        result = results[0]
        boxes = result.boxes
        
        # Check if we have tracking IDs
        if boxes.id is None:
            return tracks

        h, w = frame.shape[:2]
        reid_worker = get_reid_worker()
        
        for box, track_id in zip(boxes, boxes.id):
            tid = int(track_id.item())
            class_idx = int(box.cls[0].item())
            class_name = self.model.names[class_idx]
            
            # Map [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            
            # Extract crop for Re-ID (only for persons)
            reid_embedding = None
            if class_name == "person":
                x1, y1, x2, y2 = map(int, xyxy)
                # Ensure bounds are within frame
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x2 > x1 and y2 > y1:
                    crop = frame[y1:y2, x1:x2]
                    # Convert to JPEG quality for worker
                    _, encoded = cv2.imencode('.jpg', crop)
                    reid_embedding = reid_worker.extract_embedding(encoded.tobytes())
            
            # Normalize
            norm_box = {
                "x": float(xyxy[0] / w),
                "y": float(xyxy[1] / h),
                "w": float((xyxy[2] - xyxy[0]) / w),
                "h": float((xyxy[3] - xyxy[1]) / h)
            }

            tracks.append({
                "track_id": tid,
                "object_class": class_name,
                "bounding_box": norm_box,
                "confidence": float(box.conf[0].item()),
                "reid_embedding": reid_embedding
            })

        return tracks

_tracking_instance: Optional[PersonTrackingWorker] = None

def get_tracking_worker() -> PersonTrackingWorker:
    """Singleton instance getter."""
    global _tracking_instance
    if _tracking_instance is None:
        _tracking_instance = PersonTrackingWorker()
    return _tracking_instance
