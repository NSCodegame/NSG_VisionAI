"""Video Feed repository"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_feed import FeedStatus, FeedType, VideoFeed
from app.repositories.base import BaseRepository


class VideoFeedRepository(BaseRepository[VideoFeed]):
    """Repository for VideoFeed model"""

    def __init__(self, session: AsyncSession):
        super().__init__(VideoFeed, session)

    async def get_by_zone(self, zone_id: UUID, skip: int = 0, limit: int = 100) -> List[VideoFeed]:
        """Get feeds by security zone"""
        return await self.get_multi(
            skip=skip, limit=limit, filters=[VideoFeed.zone_id == zone_id]
        )

    async def get_by_status(
        self, status: FeedStatus, skip: int = 0, limit: int = 100
    ) -> List[VideoFeed]:
        """Get feeds by status"""
        return await self.get_multi(
            skip=skip, limit=limit, filters=[VideoFeed.status == status.value]
        )

    async def get_by_type(
        self, feed_type: FeedType, skip: int = 0, limit: int = 100
    ) -> List[VideoFeed]:
        """Get feeds by type"""
        return await self.get_multi(
            skip=skip, limit=limit, filters=[VideoFeed.feed_type == feed_type.value]
        )

    async def update_status(self, feed_id: UUID, status: FeedStatus) -> Optional[VideoFeed]:
        """Update feed status"""
        return await self.update(feed_id, status=status.value)

    async def get_active_feeds(self, skip: int = 0, limit: int = 100) -> List[VideoFeed]:
        """Get all active feeds"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[VideoFeed.status == FeedStatus.ACTIVE.value],
        )

    async def toggle_ai_processing(self, feed_id: UUID) -> Optional[VideoFeed]:
        """Toggle AI processing for feed"""
        feed = await self.get(feed_id)
        if feed is None:
            return None
        return await self.update(feed_id, ai_enabled=not feed.ai_enabled)
