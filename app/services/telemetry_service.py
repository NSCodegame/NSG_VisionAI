"""
Telemetry Service — Phase 22, Task 22.2

Orchestrates location and status updates for aerial/mobile video feeds.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.video_feed import VideoFeedRepository
from app.models.video_feed import FeedType

logger = logging.getLogger(__name__)

class TelemetryService:
    """
    Business logic for UAV telemetry and spatial awareness.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feed_repo = VideoFeedRepository(session)

    async def update_drone_location(
        self,
        feed_id: UUID,
        lat: float,
        lon: float,
        alt: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the GPS coordinates and telemetry metadata of a drone feed.
        """
        feed = await self.feed_repo.get(feed_id)
        if not feed or feed.feed_type != FeedType.DRONE:
            logger.warning("Attempted to update telemetry for non-drone feed: %s", feed_id)
            return False

        # update standard fields
        feed.latitude = Decimal(str(lat))
        feed.longitude = Decimal(str(lon))
        feed.last_active_at = datetime.utcnow()
        
        # We could also update a 'telemetry' JSON field if added to the model
        # For now, we logging movement
        logger.info("UAV %s Position: Lat %.6f, Lon %.6f, Alt %.1fm", feed_id, lat, lon, alt)
        
        await self.session.flush()
        await self.session.commit()
        return True

from datetime import datetime
