"""
Archival Service — Phase 14, Task 14.2

Manages secure video segment indexing, encryption, and object storage.
Handles retention policy enforcement and storage optimization.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.video_segment import VideoSegment
from app.repositories.video_segment import VideoSegmentRepository
from app.utils.encryption import encrypt_binary_aes_gcm
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)

class ArchivalService:
    """
    Business logic for secure video archival and retention management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.segment_repo = VideoSegmentRepository(session)

    async def archive_video_segment(
        self,
        feed_id: UUID,
        start_time: datetime,
        end_time: datetime,
        raw_video_bytes: bytes,
        has_flagged_events: bool = False
    ) -> VideoSegment:
        """
        Encrypt and archive a video segment to MinIO.
        
        Args:
            feed_id: Source feed UUID
            start_time: Segment begin
            end_time: Segment end
            raw_video_bytes: Raw binary video data (e.g. .mp4)
            has_flagged_events: Whether segment contains high-priority alerts
            
        Returns:
            The created VideoSegment metadata record.
        """
        # 1. Encrypt Segment (AES-256-GCM)
        # Using master key for now, rotation logic in Phase 28
        master_key = settings.encryption_master_key
        try:
            encrypted_bytes = encrypt_binary_aes_gcm(raw_video_bytes, master_key)
        except Exception as e:
            logger.error("Encryption failed for segment of feed %s: %s", feed_id, e)
            raise

        # 2. Upload to MinIO
        file_name = f"{feed_id}/{start_time.strftime('%Y%m%d_%H%M%S')}.mp4.enc"
        object_path = f"archive/{file_name}"
        
        success = minio_client.upload_bytes(
            encrypted_bytes, 
            object_path, 
            content_type="application/octet-stream"
        )
        
        if not success:
            raise RuntimeError(f"Failed to upload segment {object_path} to MinIO")

        # 3. Calculate Retention
        # Default retention is 30 days unless flagged
        retention_until = None
        if not has_flagged_events:
            retention_until = datetime.now(timezone.utc) + timedelta(days=settings.video_retention_days)

        # 4. Create Metadata Record
        segment = await self.segment_repo.create(
            feed_id=feed_id,
            start_timestamp=start_time,
            end_timestamp=end_time,
            storage_path=object_path,
            encryption_key_id=uuid4(), # Placeholder for KMS key ref
            file_size_bytes=len(encrypted_bytes),
            has_flagged_events=has_flagged_events,
            retention_until=retention_until,
            created_at=datetime.now(timezone.utc)
        )
        
        await self.session.commit()
        logger.info("Segment archived: Feed %s, Start %s, Path %s", 
                    feed_id, start_time, object_path)
        
        return segment

    async def cleanup_expired_segments(self) -> int:
        """Remove segments that have passed their retention period from storage and DB."""
        expired = await self.segment_repo.get_expired_segments()
        count = 0
        
        for segment in expired:
            try:
                # Remove from MinIO
                minio_client.delete_object(segment.storage_path)
                # Remove from DB
                await self.segment_repo.delete(segment.id)
                count += 1
            except Exception as e:
                logger.error("Failed to cleanup segment %s: %s", segment.id, e)
                
        await self.session.commit()
        return count
