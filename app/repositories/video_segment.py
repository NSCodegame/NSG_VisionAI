"""Video segment repository — Phase 14"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_segment import VideoSegment
from app.repositories.base import BaseRepository

class VideoSegmentRepository(BaseRepository[VideoSegment]):
    """Repository for VideoSegment model"""

    def __init__(self, session: AsyncSession):
        super().__init__(VideoSegment, session)

    async def get_by_feed_and_time(
        self, feed_id: UUID, start: datetime, end: datetime
    ) -> List[VideoSegment]:
        """Get segments for a feed within a time range"""
        result = await self.session.execute(
            select(VideoSegment).where(
                VideoSegment.feed_id == feed_id,
                VideoSegment.start_timestamp >= start,
                VideoSegment.end_timestamp <= end
            ).order_by(VideoSegment.start_timestamp.asc())
        )
        return result.scalars().all()

    async def get_expired_segments(self) -> List[VideoSegment]:
        """Get segments past their retention period"""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(VideoSegment).where(
                VideoSegment.retention_until <= now,
                VideoSegment.has_flagged_events == False
            )
        )
        return result.scalars().all()
