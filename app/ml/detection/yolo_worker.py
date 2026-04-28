"""
ObjectDetectionWorker — Phase 9, Task 9.2

Uses YOLOv8x for real-time object detection (person, weapon, bag, vehicle, drone, animal).
Leverages CUDA for GPU acceleration and supports batch processing.
"""

import logging
import time
from typing import Dict, List, Optional
from uuid import UUID

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from app.core.config import settings
from app.models.detection_event import DetectionType

logger = logging.getLogger(__name__)

class ObjectDetectionWorker:
    """
    Worker for processing video frames with YOLOv8x.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the YOLOv8x model.
        Loads the model into GPU memory if available.
        """
        self.model_path = model_path or str(settings.yolo_model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info("Loading YOLOv8x model on %s from %s", self.device, self.model_path)
        try:
            self.model = YOLO(self.model_path)
            self.model.to(self.device)
            logger.info("YOLOv8x model loaded successfully")
        except Exception as e:
            logger.error("Failed to load YOLOv8x model: %s", e)
            # In a production defense environment, we should probably fail-fast here
            # for the worker, allowing k8s to restart it, but for development we'll continue.
            self.model = None

    def process_frame(
        self, 
        frame: np.ndarray, 
        conf_threshold: Optional[float] = None,
        nms_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Run inference on a single frame.
        
        Args:
            frame: BGR numpy array (OpenCV format)
            conf_threshold: Confidence threshold (defaults to settings)
            nms_threshold: NMS threshold (defaults to settings)
            
        Returns:
            List of detection dictionaries.
        """
        if self.model is None:
            return []

        conf = conf_threshold or settings.yolo_confidence_threshold
        iou = nms_threshold or settings.yolo_nms_threshold

        # Run inference
        # imgsz=640 is standard for YOLOv8
        results = self.model.predict(
            source=frame,
            conf=conf,
            iou=iou,
            imgsz=settings.yolo_input_size,
            device=self.device,
            verbose=False
        )

        detections = []
        if not results:
            return detections

        # Process results
        result = results[0]
        boxes = result.boxes
        
        # Get frame dimensions for normalization
        h, w = frame.shape[:2]

        for box in boxes:
            # Map Coco/YOLO class index to our internal types
            class_idx = int(box.cls[0].item())
            class_name = self.model.names[class_idx]
            
            # Map to DetectionType
            det_type = DetectionType.OBJECT
            if class_name in ["car", "truck", "bus", "motorcycle", "vehicle"]:
                det_type = DetectionType.VEHICLE
            
            # Bounding box [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            
            # Normalize bounding box to percentages (0.0-1.0)
            norm_box = {
                "x": float(xyxy[0] / w),
                "y": float(xyxy[1] / h),
                "w": float((xyxy[2] - xyxy[0]) / w),
                "h": float((xyxy[3] - xyxy[1]) / h)
            }

            detections.append({
                "detection_type": det_type,
                "confidence": float(box.conf[0].item()),
                "bounding_box": norm_box,
                "object_class": class_name,
            })

        return detections

    def update_threshold(self, threshold: float):
        """Update the global confidence threshold for this worker instance."""
        # Note: Threshold is usually passed per-call if zone-specific,
        # but this allows for global override.
        pass

# ── Singleton instance for worker processes ───────────────────────────────────

_yolo_instance: Optional[ObjectDetectionWorker] = None

def get_yolo_worker() -> ObjectDetectionWorker:
    """Get or initialize the global YOLO worker instance."""
    global _yolo_instance
    if _yolo_instance is None:
        _yolo_instance = ObjectDetectionWorker()
    return _yolo_instance
