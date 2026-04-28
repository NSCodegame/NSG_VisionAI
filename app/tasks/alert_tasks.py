"""
Alert Tasks — Phase 13, Task 13.2

Celery tasks for asynchronous alert processing and notification.
"""

import logging
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.detection_event import DetectionType
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.alert_tasks.process_alert_task", queue="alert_queue")
def process_alert_task(
    event_id_str: str,
    feed_id_str: str,
    detection_type_str: str,
    confidence: float,
    object_class: str = None,
    zone_id_str: str = None
):
    """
    Celery task to evaluate a detection event for potential alerts.
    """
    import asyncio
    
    event_id = UUID(event_id_str)
    feed_id = UUID(feed_id_str)
    detection_type = DetectionType(detection_type_str)
    zone_id = UUID(zone_id_str) if zone_id_str else None
    
    async def process():
        async with AsyncSessionLocal() as session:
            alert_service = AlertService(session)
            
            # Note: Zone threat level retrieval logic will be in Phase 13 Task 13.3
            # For now, we assume GREEN unless we find a specific zone
            zone_threat_level = "GREEN"
            if zone_id:
                # In upcoming Task 13.3, we'll fetch the real threat level
                pass

            await alert_service.process_detection(
                event_id=event_id,
                feed_id=feed_id,
                detection_type=detection_type,
                confidence=confidence,
                object_class=object_class,
                zone_id=zone_id,
                zone_threat_level=zone_threat_level
            )
            
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(process())
    else:
        loop.run_until_complete(process())

    logger.debug("Alert processing completed for event %s", event_id)
