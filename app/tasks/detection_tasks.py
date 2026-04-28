"""
Object Detection Tasks — Phase 9, Task 9.2

Celery tasks for processing video frames with YOLOv8x.
"""

import base64
import io
import logging
from datetime import datetime
from uuid import UUID

import cv2
import numpy as np
from PIL import Image

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ml.detection.yolo_worker import get_yolo_worker
from app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.detection_tasks.process_frame_task", queue="detection_queue")
def process_frame_task(feed_id_str: str, frame_b64: str, timestamp_ms: int):
    """
    Celery task to detect objects in a frame.
    Runs synchronously within the worker process (which should have GPU access).
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

    # 2. Run Inference
    worker = get_yolo_worker()
    detections = worker.process_frame(frame)
    
    if not detections:
        return

    # 3. Persist Detections
    # Since this is a Celery task (sync), we need to run the async service in an event loop
    async def save_detections():
        async with AsyncSessionLocal() as session:
            service = DetectionService(session)
            for det in detections:
                await service.create_detection_event(
                    feed_id=feed_id,
                    frame_timestamp=timestamp,
                    detection_data=det,
                    frame_bytes=frame_bytes # Save raw JPEG as snapshot
                )
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This shouldn't happen in a standard Celery worker, but handle just in case
        asyncio.ensure_future(save_detections())
    else:
        loop.run_until_complete(save_detections())

    logger.info("Processed %d detections for feed %s", len(detections), feed_id)

@celery_app.task(name="app.tasks.detection_tasks.consume_stream_task")
def consume_stream_task(feed_id_str: str):
    """
    Special task that runs a long-running loop to consume from Redis Streams.
    One worker per feed (or group of feeds).
    """
    # This will be implemented if we want Celery to manage the consumer loop.
    # Alternatively, we run a standalone consumer process.
    pass
