"""
Face Detection Tasks — Phase 10, Task 10.1

Celery tasks for processing face detection and recognition.
"""

import base64
import logging
from datetime import datetime
from uuid import UUID

import cv2
import numpy as np

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ml.detection.face_worker import get_face_worker
from app.repositories.watchlist import WatchlistRepository
from app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.face_tasks.process_face_task", queue="face_queue")
def process_face_task(feed_id_str: str, frame_b64: str, timestamp_ms: int):
    """
    Celery task to detect faces and match against the watchlist.
    """
    import asyncio
    
    feed_id = UUID(feed_id_str)
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
    
    # 1. Decode frame
    try:
        frame_bytes = base64.b64decode(frame_b64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Failed to decode frame")
    except Exception as e:
        logger.error("Error decoding frame for feed %s: %s", feed_id, e)
        return

    # 2. Run Face Detection & Embedding
    worker = get_face_worker()
    face_detections = worker.detect_and_embed(frame)
    
    if not face_detections:
        return

    # 3. Match against Watchlist and Persist
    async def match_and_save():
        async with AsyncSessionLocal() as session:
            watchlist_repo = WatchlistRepository(session)
            detection_service = DetectionService(session)
            
            for face in face_detections:
                # Similarity search using pgvector
                # Threshold is currently set to 0.85 in config
                matches = await watchlist_repo.search_by_embedding(
                    embedding=face["embedding"],
                    threshold=0.85,
                    limit=1
                )
                
                watchlist_match_id = None
                if matches:
                    entry, similarity = matches[0]
                    watchlist_match_id = entry.id
                    logger.info("WATCHLIST MATCH: Person %s (ID: %s) detected in feed %s", 
                                entry.name, entry.id, feed_id)
                
                # Update detection data for service
                # Note: We can pass the facial crop to the service for snapshotting
                # We'll stick to the full frame snapshot for now as per design
                face["watchlist_match_id"] = watchlist_match_id
                
                await detection_service.create_detection_event(
                    feed_id=feed_id,
                    frame_timestamp=timestamp,
                    detection_data=face,
                    frame_bytes=frame_bytes # Snapshot full frame
                )
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(match_and_save())
    else:
        loop.run_until_complete(match_and_save())

    logger.info("Processed %d faces for feed %s", len(face_detections), feed_id)
