"""Detection Event repository with TimescaleDB optimizations"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection_event import DetectionEvent, DetectionType
from app.repositories.base import BaseRepository


class DetectionEventRepository(BaseRepository[DetectionEvent]):
    """Repository for DetectionEvent model with TimescaleDB optimizations"""

    def __init__(self, session: AsyncSession):
        super().__init__(DetectionEvent, session)

    async def get_by_feed_and_timerange(
        self,
        feed_id: UUID,
        start_time: datetime,
        end_time: datetime,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[DetectionEvent]:
        """
        Get detection events by feed and time range (TimescaleDB optimized).

        Args:
            feed_id: Feed UUID
            start_time: Start timestamp
            end_time: End timestamp
            skip: Offset
            limit: Max results

        Returns:
            List of detection events
        """
        result = await self.session.execute(
            select(DetectionEvent)
            .where(
                and_(
                    DetectionEvent.feed_id == feed_id,
                    DetectionEvent.frame_timestamp >= start_time,
                    DetectionEvent.frame_timestamp <= end_time,
                )
            )
            .order_by(DetectionEvent.frame_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_person(
        self, person_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[DetectionEvent]:
        """Get detection events for a tracked person"""
        result = await self.session.execute(
            select(DetectionEvent)
            .where(DetectionEvent.person_id == person_id)
            .order_by(DetectionEvent.frame_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_watchlist_match(
        self, watchlist_entry_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[DetectionEvent]:
        """Get detection events for a watchlist match"""
        result = await self.session.execute(
            select(DetectionEvent)
            .where(DetectionEvent.watchlist_match_id == watchlist_entry_id)
            .order_by(DetectionEvent.frame_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_object_class(
        self,
        object_class: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DetectionEvent]:
        """Search detection events by object class"""
        filters = [DetectionEvent.object_class == object_class]

        if start_time:
            filters.append(DetectionEvent.frame_timestamp >= start_time)
        if end_time:
            filters.append(DetectionEvent.frame_timestamp <= end_time)

        result = await self.session.execute(
            select(DetectionEvent)
            .where(and_(*filters))
            .order_by(DetectionEvent.frame_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_zone(
        self,
        zone_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DetectionEvent]:
        """Search detection events by zone (via feed)"""
        from app.models.video_feed import VideoFeed

        filters = [VideoFeed.zone_id == zone_id]

        if start_time:
            filters.append(DetectionEvent.frame_timestamp >= start_time)
        if end_time:
            filters.append(DetectionEvent.frame_timestamp <= end_time)

        result = await self.session.execute(
            select(DetectionEvent)
            .join(VideoFeed, DetectionEvent.feed_id == VideoFeed.id)
            .where(and_(*filters))
            .order_by(DetectionEvent.frame_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
