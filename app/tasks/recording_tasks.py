"""
Recording Tasks — Celery tasks for video recording and clip extraction

Tasks:
  - extract_alert_clip: Extract video clip around an alert event
  - save_alert_snapshot: Save annotated JPEG at alert moment
  - cleanup_all_segments: Delete expired ring-buffer segments
  - upload_clip_to_minio: Upload extracted clip to MinIO for long-term storage
"""

import asyncio
import base64
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.celery_app import celery_app
from app.services.recording_service import get_recording_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.recording_tasks.extract_alert_clip",
    queue="recording_queue",
    bind=True,
    max_retries=2,
)
def extract_alert_clip(
    self,
    feed_id: str,
    event_time_iso: str,
    alert_id: str,
    pre_seconds: int = 30,
    post_seconds: int = 30,
):
    """
    Extract a video clip around an alert event.
    Triggered automatically when a P1/P2 alert is generated.
    """
    try:
        event_time = datetime.fromisoformat(event_time_iso)
        service = get_recording_service()

        loop = asyncio.new_event_loop()
        clip_path = loop.run_until_complete(
            service.extract_clip(
                feed_id=feed_id,
                event_time=event_time,
                pre_seconds=pre_seconds,
                post_seconds=post_seconds,
                alert_id=alert_id,
            )
        )
        loop.close()

        if clip_path:
            logger.info("Alert clip extracted: %s for alert %s", clip_path, alert_id)
            # Trigger MinIO upload
            upload_clip_to_minio.delay(str(clip_path), feed_id, alert_id)
            return {"status": "success", "clip_path": str(clip_path)}
        else:
            logger.warning("No clip extracted for alert %s (no segments available)", alert_id)
            return {"status": "no_segments"}

    except Exception as exc:
        logger.error("Clip extraction failed for alert %s: %s", alert_id, exc)
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(
    name="app.tasks.recording_tasks.save_alert_snapshot",
    queue="recording_queue",
)
def save_alert_snapshot(
    feed_id: str,
    frame_b64: str,
    alert_id: str,
    detections_json: Optional[str] = None,
):
    """
    Save an annotated JPEG snapshot at the moment of an alert.
    """
    import json

    try:
        frame_bytes = base64.b64decode(frame_b64)
        detections = json.loads(detections_json) if detections_json else None
        service = get_recording_service()

        loop = asyncio.new_event_loop()
        snapshot_path = loop.run_until_complete(
            service.save_alert_snapshot(
                feed_id=feed_id,
                frame_jpeg=frame_bytes,
                alert_id=alert_id,
                detections=detections,
            )
        )
        loop.close()

        if snapshot_path:
            logger.info("Alert snapshot saved: %s", snapshot_path)
            return {"status": "success", "snapshot_path": str(snapshot_path)}
        return {"status": "failed"}

    except Exception as exc:
        logger.error("Snapshot save failed for alert %s: %s", alert_id, exc)
        return {"status": "error", "error": str(exc)}


@celery_app.task(
    name="app.tasks.recording_tasks.cleanup_all_segments",
    queue="recording_queue",
)
def cleanup_all_segments():
    """
    Delete expired ring-buffer segments for all feeds.
    Runs every 30 minutes via Celery Beat.
    """
    from app.services.recording_service import RECORDING_DIR

    service = get_recording_service()
    total_deleted = 0

    if RECORDING_DIR.exists():
        for feed_dir in RECORDING_DIR.iterdir():
            if feed_dir.is_dir():
                deleted = service.cleanup_old_segments(feed_dir.name)
                total_deleted += deleted

    logger.info("Segment cleanup: deleted %d expired segments", total_deleted)
    return {"deleted": total_deleted}


@celery_app.task(
    name="app.tasks.recording_tasks.upload_clip_to_minio",
    queue="recording_queue",
    bind=True,
    max_retries=3,
)
def upload_clip_to_minio(self, clip_path: str, feed_id: str, alert_id: str):
    """
    Upload an extracted clip to MinIO for long-term archival.
    """
    try:
        from pathlib import Path
        from app.utils.minio_client import get_minio_client
        from app.core.config import settings

        clip = Path(clip_path)
        if not clip.exists():
            logger.warning("Clip not found for upload: %s", clip_path)
            return {"status": "not_found"}

        client = get_minio_client()
        object_name = f"clips/{feed_id}/{alert_id}/{clip.name}"

        client.fput_object(
            bucket_name=settings.minio_bucket_name,
            object_name=object_name,
            file_path=clip_path,
            content_type="video/mp4",
        )

        # Delete local file after successful upload
        clip.unlink(missing_ok=True)
        logger.info("Clip uploaded to MinIO: %s", object_name)
        return {"status": "uploaded", "object_name": object_name}

    except Exception as exc:
        logger.error("MinIO upload failed for clip %s: %s", clip_path, exc)
        raise self.retry(exc=exc, countdown=30)
