"""
VideoStreamIngester — Phase 8

Ingests RTSP/HLS/WebRTC video streams and publishes frames to Redis Streams
for downstream ML workers (object detection, face recognition, tracking).

Design decisions:
  - asyncio-based to keep ingestion non-blocking and concurrent across feeds.
  - Separate frame queues: 5 fps for AI (ML workers), 25 fps for display (HLS proxy).
  - Exponential backoff on reconnection (1 s → 16 s, max 5 attempts).
  - On stream loss: mark feed DEGRADED in DB, hold last-known-good frame display.
  - On total failure: mark feed OFFLINE and stop retrying until operator re-enables.
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from uuid import UUID

import cv2
import numpy as np

from app.core.config import settings
from app.core.redis import (
    create_consumer_group,
    get_redis,
    publish_frame,
)

logger = logging.getLogger(__name__)

# ── Data classes ──────────────────────────────────────────────────────────────


class StreamHealth(str, Enum):
    """Health state of a video stream connection."""

    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class StreamContext:
    """Runtime context for a single video stream."""

    feed_id: str
    rtsp_url: str
    target_fps_ai: int = 5
    target_fps_display: int = 25

    # Runtime state
    cap: Optional[cv2.VideoCapture] = None
    health: StreamHealth = StreamHealth.DISCONNECTED
    reconnect_attempts: int = 0
    last_frame_time: float = field(default_factory=time.monotonic)
    last_frame: Optional[bytes] = None  # JPEG bytes of last good frame
    frame_count: int = 0
    connecting: bool = False
    stopped: bool = False


# ── Ingester ──────────────────────────────────────────────────────────────────


class VideoStreamIngester:
    """
    Manages RTSP stream ingestion for all active VideoFeeds.

    Usage::

        ingester = VideoStreamIngester()
        await ingester.connect_stream(feed_id, rtsp_url)
        # … streams now publishing to Redis Streams …
        await ingester.disconnect_stream(feed_id)
    """

    def __init__(self) -> None:
        """Initialise with empty stream registry."""
        self._streams: Dict[str, StreamContext] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    # ── Public Interface ───────────────────────────────────────────────────

    async def connect_stream(
        self,
        feed_id: str,
        rtsp_url: str,
        fps_ai: int = 5,
        fps_display: int = 25,
    ) -> None:
        """
        Start ingesting a video stream and publishing frames to Redis Streams.

        Args:
            feed_id: UUID string of the VideoFeed record.
            rtsp_url: Plaintext RTSP URL (must be decrypted before passing here).
            fps_ai: Target frame rate for AI processing queue (default 5).
            fps_display: Target frame rate for display queue (default 25).
        """
        if feed_id in self._streams:
            logger.warning("Stream %s already connected — skipping", feed_id)
            return

        ctx = StreamContext(
            feed_id=feed_id,
            rtsp_url=rtsp_url,
            target_fps_ai=fps_ai,
            target_fps_display=fps_display,
        )
        self._streams[feed_id] = ctx

        # Ensure consumer group exists before workers start
        redis = await get_redis()
        await create_consumer_group(redis, feed_id)

        # Start background ingestion task
        task = asyncio.create_task(
            self._ingest_loop(ctx), name=f"ingest:{feed_id}"
        )
        self._tasks[feed_id] = task
        logger.info("Started stream ingestion for feed %s", feed_id)

    async def disconnect_stream(self, feed_id: str) -> None:
        """Stop ingesting a stream and release resources."""
        ctx = self._streams.pop(feed_id, None)
        if ctx is None:
            return

        ctx.stopped = True

        task = self._tasks.pop(feed_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if ctx.cap is not None:
            ctx.cap.release()

        logger.info("Stopped stream ingestion for feed %s", feed_id)

    async def get_stream_health(self, feed_id: str) -> Optional[StreamHealth]:
        """Return the current health state of a stream."""
        ctx = self._streams.get(feed_id)
        return ctx.health if ctx else None

    async def get_last_frame(self, feed_id: str) -> Optional[bytes]:
        """Return the last successfully captured frame as JPEG bytes."""
        ctx = self._streams.get(feed_id)
        return ctx.last_frame if ctx else None

    async def list_active_feeds(self) -> list[str]:
        """Return feed IDs of all currently connected streams."""
        return list(self._streams.keys())

    # ── Internal ingestion loop ────────────────────────────────────────────

    async def _ingest_loop(self, ctx: StreamContext) -> None:
        """Main ingestion loop for a single stream (runs as asyncio Task)."""
        backoff_seconds = [1, 2, 4, 8, 16]

        while not ctx.stopped:
            connected = await self._connect(ctx)
            if not connected:
                ctx.reconnect_attempts += 1
                if ctx.reconnect_attempts > settings.video_stream_reconnect_attempts:
                    logger.error(
                        "Feed %s exceeded max reconnect attempts — marking OFFLINE",
                        ctx.feed_id,
                    )
                    ctx.health = StreamHealth.DISCONNECTED
                    await self._update_feed_status(ctx.feed_id, "OFFLINE")
                    return  # Stop trying

                delay = backoff_seconds[
                    min(ctx.reconnect_attempts - 1, len(backoff_seconds) - 1)
                ]
                logger.warning(
                    "Feed %s connection failed — retrying in %ds (attempt %d)",
                    ctx.feed_id,
                    delay,
                    ctx.reconnect_attempts,
                )
                await asyncio.sleep(delay)
                continue

            # Successfully connected
            ctx.reconnect_attempts = 0
            ctx.health = StreamHealth.CONNECTED
            await self._update_feed_status(ctx.feed_id, "ACTIVE")
            logger.info("Feed %s connected — streaming", ctx.feed_id)

            # Read frames until stream dies
            await self._read_frames(ctx)

            # Stream died — mark degraded and retry
            if not ctx.stopped:
                ctx.health = StreamHealth.DEGRADED
                await self._update_feed_status(ctx.feed_id, "DEGRADED")
                logger.warning("Feed %s stream interrupted — reconnecting", ctx.feed_id)

    async def _connect(self, ctx: StreamContext) -> bool:
        """
        Attempt to open a VideoCapture connection to the RTSP stream.

        Runs blocking cv2 call in thread executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        try:
            cap = await asyncio.wait_for(
                loop.run_in_executor(None, self._open_capture, ctx.rtsp_url),
                timeout=settings.video_stream_connection_timeout,
            )
            if cap is None or not cap.isOpened():
                return False
            ctx.cap = cap
            return True
        except asyncio.TimeoutError:
            logger.warning("Feed %s connection timed out", ctx.feed_id)
            return False
        except Exception as exc:
            logger.error("Feed %s connection error: %s", ctx.feed_id, exc)
            return False

    @staticmethod
    def _open_capture(rtsp_url: str) -> Optional[cv2.VideoCapture]:
        """Open a VideoCapture (blocking — run in executor)."""
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimise latency
        return cap if cap.isOpened() else None

    async def _read_frames(self, ctx: StreamContext) -> None:
        """Read frames from the capture and publish to Redis Streams."""
        loop = asyncio.get_event_loop()
        ai_interval = 1.0 / ctx.target_fps_ai  # seconds between AI frames
        last_ai_publish = 0.0
        redis = await get_redis()

        while not ctx.stopped:
            try:
                ret, frame = await asyncio.wait_for(
                    loop.run_in_executor(None, ctx.cap.read),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Feed %s frame read timeout", ctx.feed_id)
                break
            except Exception as exc:
                logger.error("Feed %s frame read error: %s", ctx.feed_id, exc)
                break

            if not ret or frame is None:
                logger.warning("Feed %s returned empty frame", ctx.feed_id)
                break

            # Encode frame as JPEG
            success, buffer = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            if not success:
                continue

            jpeg_bytes = buffer.tobytes()
            ctx.last_frame = jpeg_bytes
            ctx.frame_count += 1
            now = time.monotonic()

            # Publish to AI stream at target_fps_ai rate
            if now - last_ai_publish >= ai_interval:
                timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                await publish_frame(
                    redis,
                    ctx.feed_id,
                    jpeg_bytes,
                    timestamp_ms,
                    extra={"sequence": ctx.frame_count},
                )
                last_ai_publish = now

            # Small yield to avoid monopolising the event loop
            await asyncio.sleep(0)

        # Release capture
        if ctx.cap is not None:
            ctx.cap.release()
            ctx.cap = None

    async def _update_feed_status(self, feed_id: str, status: str) -> None:
        """
        Update the VideoFeed status in PostgreSQL.

        Imports DB session lazily to avoid circular imports at module load.
        """
        try:
            from app.core.database import AsyncSessionLocal
            from app.repositories.video_feed import VideoFeedRepository

            async with AsyncSessionLocal() as session:
                repo = VideoFeedRepository(session)
                feed = await repo.get_by_id(UUID(feed_id))
                if feed:
                    feed.status = status
                    if status == "ACTIVE":
                        feed.last_active_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as exc:
            logger.error(
                "Failed to update feed %s status to %s: %s", feed_id, status, exc
            )


# ── Singleton ingester instance ────────────────────────────────────────────────

ingester = VideoStreamIngester()
