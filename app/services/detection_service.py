"""
Detection Event Service — Phase 9, Task 9.3

Handles the persistence of AI detection results, including database storage
and frame snapshot archival in MinIO.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detection_event import DetectionEvent, DetectionThreatLevel, DetectionType
from app.repositories.detection_event import DetectionEventRepository
from app.tasks.alert_tasks import process_alert_task
from app.utils.encryption import encrypt_aes_gcm
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)

class DetectionService:
    """
    Business logic for processing and persisting detection events.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.detection_repo = DetectionEventRepository(session)

    async def create_detection_event(
        self,
        feed_id: UUID,
        frame_timestamp: datetime,
        detection_data: Dict,
        frame_bytes: Optional[bytes] = None
    ) -> DetectionEvent:
        """
        Create a new detection event and optionally save a snapshot.
        
        Args:
            feed_id: Source video feed UUID
            frame_timestamp: Timestamp when the frame was captured
            detection_data: Dict containing detection_type, confidence, bounding_box, object_class
            frame_bytes: Raw JPEG bytes of the frame (unencrypted)
            
        Returns:
            The created DetectionEvent instance.
        """
        
        # 1. Handle Frame Snapshot (Phase 14 integration)
        snapshot_path = None
        if frame_bytes:
            # Encrypt frame bytes using the master key (stored as base64 in MinIO for this simplified version)
            # In Phase 14, we'll refine this with per-segment keys.
            encrypted_frame = encrypt_aes_gcm(
                frame_bytes.hex(), # Using hex as a way to "string-ify" the bytes for our current utility
                settings.encryption_master_key
            )
            
            # Construct path: {feed_id}/{year}/{month}/{day}/{timestamp}.enc
            ts_str = frame_timestamp.strftime("%H%M%S_%f")
            date_path = frame_timestamp.strftime("%Y/%m/%d")
            snapshot_path = f"snapshots/{feed_id}/{date_path}/{ts_str}.enc"
            
            success = minio_client.upload_bytes(
                encrypted_frame.encode(), 
                snapshot_path,
                content_type="application/octet-stream"
            )
            if not success:
                logger.error("Failed to upload frame snapshot for feed %s", feed_id)
                snapshot_path = None

        # 2. Determine Initial Threat Level
        confidence = detection_data.get("confidence", 0.0)
        threat_level = DetectionThreatLevel.LOW
        
        # Priority mapping for specific objects or watchlist matches
        watchlist_match_id = detection_data.get("watchlist_match_id")
        if watchlist_match_id:
            threat_level = DetectionThreatLevel.HIGH
        elif detection_data.get("object_class") in ["weapon", "pistol", "rifle"]:
            threat_level = DetectionThreatLevel.CRITICAL
        elif confidence > 0.9:
            threat_level = DetectionThreatLevel.MEDIUM
            
        # 3. Create Database Record
        event = await self.detection_repo.create(
            id=None,
            frame_timestamp=frame_timestamp,
            feed_id=feed_id,
            detection_type=detection_data.get("detection_type", DetectionType.OBJECT),
            confidence_score=confidence,
            bounding_box=detection_data.get("bounding_box", {}),
            object_class=detection_data.get("object_class"),
            threat_level=threat_level.value,
            frame_snapshot_path=snapshot_path,
            watchlist_match_id=watchlist_match_id,
            person_id=detection_data.get("person_id"),
            processed_at=datetime.now(timezone.utc)
        )
        
        # 4. Trigger Alert Processing
        process_alert_task.delay(
            event_id_str=str(event.id),
            feed_id_str=str(feed_id),
            detection_type_str=event.detection_type,
            confidence=float(event.confidence_score),
            object_class=event.object_class,
            zone_id_str=None # Zone correlation implemented in Phase 13 Task 13.3
        )
        
        await self.session.commit()
        return event

    async def get_detections_for_feed(
        self,
        feed_id: UUID,
        start_time: datetime,
        end_time: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[DetectionEvent]:
        """Retrieve detections for a specific feed and time range."""
        return await self.detection_repo.get_by_feed_and_timerange(
            feed_id, start_time, end_time, skip, limit
        )
