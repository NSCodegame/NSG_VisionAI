"""
Anomaly Detection Tasks — Phase 12, Task 12.1

Celery tasks for processing temporal trajectory anomalies.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ml.anomaly.lstm_worker import get_anomaly_worker
from app.models.detection_event import DetectionType, DetectionThreatLevel
from app.repositories.tracked_person import TrackedPersonRepository
from app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.anomaly_tasks.detect_anomalies_task", queue="anomaly_queue")
def detect_anomalies_task(person_id_str: str):
    """
    Celery task to analyze person trajectory for anomalies.
    """
    import asyncio
    
    person_id = UUID(person_id_str)
    
    async def analyze():
        async with AsyncSessionLocal() as session:
            person_repo = TrackedPersonRepository(session)
            detection_service = DetectionService(session)
            
            # 1. Fetch person and trajectory
            person = await person_repo.get(person_id)
            if not person or not person.trajectory or "points" not in person.trajectory:
                return
            
            points_data = person.trajectory["points"]
            if len(points_data) < 10: # Minimum window to detect pattern
                return
                
            # Extract (x, y) coordinates
            points = [
                (p["position"]["x"], p["position"]["y"]) 
                for p in points_data[-30:] # Last 30 points as per config
            ]
            
            # 2. Run Anomaly Detection
            worker = get_anomaly_worker()
            score = worker.compute_anomaly_score(points)
            
            # 3. Create Event if Anomalous
            if score > worker.threshold:
                logger.warning("ANOMALY DETECTED for person %s, score: %.2f", person_id, score)
                
                # Fetch last known feed_id and timestamp from trajectory
                last_point = points_data[-1]
                feed_id = UUID(last_point["feed_id"])
                # Handle isoformat string or datetime object
                ts_str = last_point["timestamp"]
                if isinstance(ts_str, str):
                    timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                else:
                    timestamp = ts_str
                
                await detection_service.create_detection_event(
                    feed_id=feed_id,
                    frame_timestamp=timestamp,
                    detection_data={
                        "detection_type": DetectionType.ANOMALY,
                        "confidence": score,
                        "object_class": "suspicious_movement",
                        "person_id": person_id,
                        # Anomaly bounding box is the last known position
                        "bounding_box": last_point["position"] 
                    }
                )
    
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(analyze())
    else:
        loop.run_until_complete(analyze())

    logger.debug("Anomaly analysis completed for person %s", person_id)
