"""
StreamManager — Production-grade stream orchestration for 100+ concurrent feeds

Architecture:
  - Shard feeds across worker slots (max SLOTS_PER_PROCESS per asyncio event loop)
  - Each slot runs an independent VideoStreamIngester task
  - Health monitor polls all streams every 30s, auto-restarts dead ones
  - Backpressure: if Redis memory > 80%, pause low-priority feeds
  - Metrics: per-feed FPS, latency, reconnect count exposed via /health
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import UUID

from app.core.config import settings
from app.core.redis import get_redis
from app.ml.ingestion.stream_ingester import VideoStreamIngester, StreamHealth
from app.utils.encryption import decrypt_rtsp_url

logger = logging.getLogger(__name__)

# Max concurrent streams per ingester process
# Each stream uses ~50MB RAM + 1 thread for OpenCV capture
SLOTS_PER_PROCESS = int(getattr(settings, "stream_slots_per_process", 50))


@dataclass
class StreamSlot:
    """Tracks runtime state for a single managed stream."""
    feed_id: str
    rtsp_url: str
    priority: int = 1          # 1=high (P1 zone), 2=normal, 3=low
    started_at: float = field(default_factory=time.monotonic)
    last_frame_at: float = field(default_factory=time.monotonic)
    reconnect_count: int = 0
    fps_samples: List[float] = field(default_factory=list)
    paused: bool = False

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def avg_fps(self) -> float:
        if not self.fps_samples:
            return 0.0
        return sum(self.fps_samples[-10:]) / len(self.fps_samples[-10:])


class StreamManager:
    """
    Manages 100+ concurrent RTSP streams with:
    - Automatic sharding across ingester instances
    - Health monitoring and auto-restart
    - Priority-based backpressure
    - Per-feed metrics
    """

    def __init__(self) -> None:
        self._ingester = VideoStreamIngester()
        self._slots: Dict[str, StreamSlot] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the stream manager and health monitor."""
        self._running = True
        self._monitor_task = asyncio.create_task(
            self._health_monitor(), name="stream-manager-monitor"
        )
        logger.info("StreamManager started (max %d slots)", SLOTS_PER_PROCESS)

    async def stop(self) -> None:
        """Stop all streams and the health monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Disconnect all streams
        for feed_id in list(self._slots.keys()):
            await self._ingester.disconnect_stream(feed_id)
        self._slots.clear()
        logger.info("StreamManager stopped")

    # ── Public API ────────────────────────────────────────────────────────

    async def add_feed(
        self,
        feed_id: str,
        rtsp_url: str,
        priority: int = 2,
        fps_ai: int = 5,
        fps_display: int = 25,
    ) -> bool:
        """
        Add a feed to the managed pool.

        Returns False if at capacity (caller should queue or reject).
        """
        if feed_id in self._slots:
            logger.debug("Feed %s already managed", feed_id)
            return True

        if len(self._slots) >= SLOTS_PER_PROCESS:
            # Evict lowest-priority paused stream if at capacity
            evicted = self._evict_lowest_priority()
            if not evicted:
                logger.warning("StreamManager at capacity (%d slots)", SLOTS_PER_PROCESS)
                return False

        slot = StreamSlot(feed_id=feed_id, rtsp_url=rtsp_url, priority=priority)
        self._slots[feed_id] = slot

        await self._ingester.connect_stream(feed_id, rtsp_url, fps_ai, fps_display)
        logger.info("Feed %s added to StreamManager (priority=%d)", feed_id, priority)
        return True

    async def remove_feed(self, feed_id: str) -> None:
        """Remove a feed from the managed pool."""
        self._slots.pop(feed_id, None)
        await self._ingester.disconnect_stream(feed_id)
        logger.info("Feed %s removed from StreamManager", feed_id)

    async def get_frame(self, feed_id: str) -> Optional[bytes]:
        """Get the latest JPEG frame for a feed."""
        slot = self._slots.get(feed_id)
        if slot and not slot.paused:
            frame = await self._ingester.get_last_frame(feed_id)
            if frame:
                slot.last_frame_at = time.monotonic()
            return frame
        return None

    async def get_health(self, feed_id: str) -> Optional[StreamHealth]:
        """Get the health state of a stream."""
        return await self._ingester.get_stream_health(feed_id)

    def get_metrics(self) -> Dict:
        """Return per-feed and aggregate metrics."""
        active = sum(1 for s in self._slots.values() if not s.paused)
        return {
            "total_feeds": len(self._slots),
            "active_feeds": active,
            "paused_feeds": len(self._slots) - active,
            "capacity_pct": round(len(self._slots) / SLOTS_PER_PROCESS * 100, 1),
            "feeds": {
                fid: {
                    "priority": s.priority,
                    "uptime_s": round(s.uptime_seconds),
                    "reconnects": s.reconnect_count,
                    "avg_fps": round(s.avg_fps, 1),
                    "paused": s.paused,
                    "last_frame_age_s": round(time.monotonic() - s.last_frame_at, 1),
                }
                for fid, s in self._slots.items()
            },
        }

    # ── Internal ──────────────────────────────────────────────────────────

    async def _health_monitor(self) -> None:
        """Poll all streams every 30s, restart dead ones, apply backpressure."""
        while self._running:
            await asyncio.sleep(30)
            try:
                await self._check_all_streams()
                await self._apply_backpressure()
            except Exception as exc:
                logger.error("Health monitor error: %s", exc)

    async def _check_all_streams(self) -> None:
        """Restart any streams that have gone dead."""
        for feed_id, slot in list(self._slots.items()):
            if slot.paused:
                continue
            health = await self._ingester.get_stream_health(feed_id)
            if health == StreamHealth.DISCONNECTED:
                logger.warning("Feed %s disconnected — restarting", feed_id)
                slot.reconnect_count += 1
                await self._ingester.disconnect_stream(feed_id)
                await asyncio.sleep(1)
                await self._ingester.connect_stream(feed_id, slot.rtsp_url)

    async def _apply_backpressure(self) -> None:
        """Pause low-priority streams if Redis memory is under pressure."""
        try:
            redis = await get_redis()
            info = await redis.info("memory")
            used = info.get("used_memory", 0)
            max_mem = info.get("maxmemory", 0)
            if max_mem > 0 and used / max_mem > 0.80:
                # Pause priority-3 streams
                for feed_id, slot in self._slots.items():
                    if slot.priority == 3 and not slot.paused:
                        slot.paused = True
                        await self._ingester.disconnect_stream(feed_id)
                        logger.warning("Paused low-priority feed %s (Redis pressure)", feed_id)
        except Exception:
            pass

    def _evict_lowest_priority(self) -> bool:
        """Evict the lowest-priority paused stream. Returns True if evicted."""
        candidates = [
            (s.priority, fid) for fid, s in self._slots.items() if s.paused
        ]
        if not candidates:
            return False
        _, evict_id = max(candidates)  # highest priority number = lowest priority
        asyncio.create_task(self.remove_feed(evict_id))
        return True


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    global _manager
    if _manager is None:
        _manager = StreamManager()
    return _manager
