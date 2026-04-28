"""
Archival Tasks — Phase 14, Task 14.2

Celery tasks for scheduled video archival and retention management.
"""

import logging
import base64
from datetime import datetime, timezone
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.archival_service import ArchivalService

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.archival_tasks.archive_segment_task", queue="archival_queue")
def archive_segment_task(
    feed_id_str: str,
    start_time_iso: str,
    end_time_iso: str,
    video_data_b64: str,
    has_flagged_events: bool = False
):
    """
    Celery task to encrypt and archive a video segment.
    """
    import asyncio
    
    feed_id = UUID(feed_id_str)
    start_time = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))
    video_bytes = base64.b64decode(video_data_b64)
    
    async def run_archival():
        async with AsyncSessionLocal() as session:
            service = ArchivalService(session)
            await service.archive_video_segment(
                feed_id=feed_id,
                start_time=start_time,
                end_time=end_time,
                raw_video_bytes=video_bytes,
                has_flagged_events=has_flagged_events
            )
            
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(run_archival())
    else:
        loop.run_until_complete(run_archival())

@celery_app.task(name="app.tasks.archival_tasks.cleanup_retention_task", queue="archival_queue")
def cleanup_retention_task():
    """
    Periodic task to cleanup expired video segments.
    """
    import asyncio
    
    async def run_cleanup():
        async with AsyncSessionLocal() as session:
            service = ArchivalService(session)
            count = await service.cleanup_expired_segments()
            logger.info("Cleanup completed: Removed %d expired segments", count)
            
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(run_cleanup())
    else:
        loop.run_until_complete(run_cleanup())
