"""
FaceDetectionWorker — Phase 10, Task 10.1

Uses RetinaFace for detection and ArcFace for embedding extraction.
Integrated with pgvector for real-time watchlist matching.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from deepface import DeepFace

from app.core.config import settings
from app.models.detection_event import DetectionType

logger = logging.getLogger(__name__)

class FaceDetectionWorker:
    """
    Worker for processing video frames to detect and recognize faces.
    """

    def __init__(self):
        """
        Initialize the models. 
        DeepFace handles lazy loading, but we'll warm them up.
        """
        self.detector_backend = "retinaface"
        self.model_name = "ArcFace"
        self.enforce_detection = True
        self.detector_threshold = settings.retinaface_confidence_threshold
        
        logger.info("Initializing FaceDetectionWorker (RetinaFace + ArcFace)")
        # Pre-warm models to avoid latency on first frame
        try:
            # We'll run a dummy inference to trigger model download/loading if needed
            dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
            DeepFace.build_model(self.model_name)
            logger.info("Face recognition models initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize face models: %s", e)

    def detect_and_embed(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in a frame and extract their embeddings.
        
        Args:
            frame: BGR image (OpenCV format)
            
        Returns:
            List of face detections with embeddings and bounding boxes.
        """
        try:
            # extract_faces returns detections with 'face', 'facial_area', 'confidence'
            faces = DeepFace.extract_faces(
                img_path=frame,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )
        except Exception as e:
            logger.error("Error during face extraction: %s", e)
            return []

        results = []
        h, w = frame.shape[:2]

        for face_data in faces:
            conf = face_data.get("confidence", 0)
            if conf < self.detector_threshold:
                continue

            # Facial area: [x, y, w, h]
            area = face_data.get("facial_area", {})
            ax, ay, aw, ah = area.get("x"), area.get("y"), area.get("w"), area.get("h")
            
            # Normalize bounding box
            norm_box = {
                "x": float(ax / w),
                "y": float(ay / h),
                "w": float(aw / w),
                "h": float(ah / h)
            }

            # Generate embedding
            # Represent generates embeddings for the cropped/aligned face
            try:
                # DeepFace.represent returns a list of result dicts
                # We already have the crop from extract_faces, but represent can 
                # take the whole image and detection area to be more efficient if we wanted.
                # However, DeepFace usually re-runs detection in represent if not careful.
                # To be precise, we pass the extracted face image.
                face_img = face_data.get("face")
                embeddings = DeepFace.represent(
                    img_path=face_img,
                    model_name=self.model_name,
                    enforce_detection=False,
                    detector_backend="skip" # Already detected/aligned
                )
                
                if embeddings:
                    embedding = embeddings[0].get("embedding")
                    results.append({
                        "detection_type": DetectionType.FACE,
                        "confidence": float(conf),
                        "bounding_box": norm_box,
                        "embedding": embedding,
                        "face_img": face_img # Scaled facial crop
                    })
            except Exception as e:
                logger.error("Embedding extraction failed: %s", e)
                continue

        return results

_face_worker: Optional[FaceDetectionWorker] = None

def get_face_worker() -> FaceDetectionWorker:
    """Singleton instance getter."""
    global _face_worker
    if _face_worker is None:
        _face_worker = FaceDetectionWorker()
    return _face_worker
