"""
WebRTCIngester — Phase 8, Task 8.3

Handles encrypted WebRTC stream ingestion for drone feeds.
Uses aiortc for DTLS-SRTP encrypted connections.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.mediastreams import MediaStreamError

from app.core.config import settings
from app.core.redis import get_redis, publish_frame

logger = logging.getLogger(__name__)

class VideoTransformTrack(VideoStreamTrack):
    """
    A video stream track that transforms frames from an incoming track.
    Used to extract frames for publishing to Redis Streams.
    """
    def __init__(self, track: VideoStreamTrack, feed_id: str, fps_ai: int = 5):
        super().__init__()
        self.track = track
        self.feed_id = feed_id
        self.fps_ai = fps_ai
        self.ai_interval = 1.0 / fps_ai
        self.last_ai_publish = 0.0
        self.frame_count = 0

    async def recv(self):
        frame = await self.track.recv()
        self.frame_count += 1
        
        # Convert to numpy array
        img = frame.to_ndarray(format="bgr24")
        
        now = time.monotonic()
        if now - self.last_ai_publish >= self.ai_interval:
            # Encode to JPEG
            success, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                jpeg_bytes = buffer.tobytes()
                timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                
                redis = await get_redis()
                await publish_frame(
                    redis,
                    self.feed_id,
                    jpeg_bytes,
                    timestamp_ms,
                    extra={"sequence": self.frame_count, "type": "drone"}
                )
                self.last_ai_publish = now
        
        return frame

class WebRTCIngester:
    """
    Handles WebRTC ingestion for drone/body camera feeds.
    Typically triggered by a signaling exchange (Phase 22).
    """

    def __init__(self) -> None:
        self._pcs: Dict[str, RTCPeerConnection] = {}

    async def create_connection(self, feed_id: str, offer_sdp: str, offer_type: str = "offer") -> str:
        """
        Initialize a WebRTC connection for a given feed.
        Returns the answer SDP.
        """
        pc = RTCPeerConnection()
        self._pcs[feed_id] = pc

        @pc.on("track")
        def on_track(track):
            if track.kind == "video":
                logger.info("WebRTC video track received for feed %s", feed_id)
                # Wrap track to process and publish frames
                transform = VideoTransformTrack(track, feed_id)
                asyncio.ensure_future(self._consume_track(transform))

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("WebRTC connection state for %s: %s", feed_id, pc.connectionState)
            if pc.connectionState in ["failed", "closed"]:
                await self.stop_connection(feed_id)

        # Set remote description
        offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
        await pc.setRemoteDescription(offer)

        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return pc.localDescription.sdp

    async def _consume_track(self, track: VideoTransformTrack):
        """Continuously receive frames from the track."""
        try:
            while True:
                await track.recv()
        except (MediaStreamError, asyncio.CancelledError):
            logger.info("WebRTC track consumption stopped for %s", track.feed_id)

    async def stop_connection(self, feed_id: str):
        """Close the WebRTC connection for a feed."""
        pc = self._pcs.pop(feed_id, None)
        if pc:
            await pc.close()
            logger.info("WebRTC connection closed for feed %s", feed_id)

webrtc_ingester = WebRTCIngester()
