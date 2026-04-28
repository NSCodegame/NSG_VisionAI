"""
Ingester Management Service — Phase 8

Manages the lifecycle of VideoStreamIngester (RTSP) and WebRTCIngester (Drone) tasks.
Coordinates between the database (VideoFeed status) and the active ingestion tasks.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.ingestion.stream_ingester import ingester as rtsp_ingester
from app.ml.ingestion.webrtc_ingester import webrtc_ingester
from app.models.video_feed import FeedStatus, FeedType
from app.repositories.audit_log import AuditLogRepository
from app.repositories.video_feed import VideoFeedRepository
from app.utils.encryption import decrypt_rtsp_url

logger = logging.getLogger(__name__)

class IngesterService:
    """
    Manages active video ingestion tasks.
    Acts as a bridge between the API/DB and the background ML ingestion loops.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feed_repo = VideoFeedRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def start_all_active_feeds(self) -> int:
        """
        Start ingestion for all feeds marked as ACTIVE in the database.
        Typically called on application startup.
        """
        active_feeds = await self.feed_repo.get_multi(
            filters=[VideoFeedRepository.model.status == FeedStatus.ACTIVE.value]
        )
        
        started_count = 0
        for feed in active_feeds:
            try:
                await self.start_ingester(feed.id)
                started_count += 1
            except Exception as e:
                logger.error("Failed to start ingester for feed %s: %s", feed.id, e)
                
        return started_count

    async def start_ingester(self, feed_id: UUID) -> bool:
        """
        Start the appropriate ingester for a single feed.
        """
        feed = await self.feed_repo.get(feed_id)
        if not feed:
            logger.error("Feed %s not found", feed_id)
            return False

        if feed.feed_type == FeedType.DRONE.value:
            # WebRTC ingestion is usually triggered by a signaling offer
            # For now, we just acknowledge it's managed by WebRTCIngester
            logger.info("WebRTC ingester for drone feed %s initialized", feed_id)
            return True
        else:
            # RTSP ingestion (Fixed, Bodycam, Legacy)
            rtsp_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
            await rtsp_ingester.connect_stream(
                feed_id=str(feed_id),
                rtsp_url=rtsp_url,
                fps_ai=settings.video_stream_fps_ai,
                fps_display=settings.video_stream_fps_display
            )
            return True

    async def stop_ingester(self, feed_id: UUID) -> bool:
        """
        Stop ingestion for a single feed.
        """
        # Stop RTSP ingester if active
        await rtsp_ingester.disconnect_stream(str(feed_id))
        
        # Stop WebRTC connection if active
        await webrtc_ingester.stop_connection(str(feed_id))
        
        # Update status in DB if needed (usually handled by the ingester itself on failure,
        # but here we might want to mark it OFFLINE/MAINTENANCE if manually stopped).
        return True

    async def restart_ingester(self, feed_id: UUID) -> bool:
        """
        Restart an ingester.
        """
        await self.stop_ingester(feed_id)
        return await self.start_ingester(feed_id)

    async def get_all_ingesters_status(self) -> List[Dict]:
        """
        Return a list of all active ingesters and their health.
        """
        active_rtsp = await rtsp_ingester.list_active_feeds()
        status_list = []
        
        for fid in active_rtsp:
            health = await rtsp_ingester.get_stream_health(fid)
            status_list.append({
                "feed_id": fid,
                "type": "RTSP",
                "status": health
            })
            
        # WebRTC active connections
        for fid in webrtc_ingester._pcs.keys():
            status_list.append({
                "feed_id": fid,
                "type": "WebRTC",
                "status": "CONNECTED" # Simplified
            })
            
        return status_list
