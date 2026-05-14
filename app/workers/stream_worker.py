"""
Stream Worker — Standalone process for RTSP ingestion at scale

Runs independently of the FastAPI server.
Loads all ACTIVE feeds from the database and starts ingestion.
Handles failover: if a feed dies, restarts it automatically.

Usage:
  python -m app.workers.stream_worker

Docker:
  command: python -m app.workers.stream_worker

Kubernetes:
  See k8s/stream-ingester-deployment.yaml
  Scale with: kubectl scale deployment nsg-stream-ingester --replicas=3
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stream_worker")

# Worker slot assignment — distribute feeds across worker instances
# Worker 0 handles feeds 0,3,6,... Worker 1 handles 1,4,7,... etc.
WORKER_INDEX = int(os.environ.get("WORKER_INDEX", "0"))
WORKER_COUNT = int(os.environ.get("WORKER_COUNT", "1"))
SLOTS_PER_PROCESS = int(os.environ.get("STREAM_SLOTS_PER_PROCESS", "50"))


async def main() -> None:
    """Main entry point for the stream worker process."""
    logger.info(
        "Stream worker starting (index=%d/%d, slots=%d)",
        WORKER_INDEX, WORKER_COUNT, SLOTS_PER_PROCESS,
    )

    # Import here to avoid circular imports at module level
    from app.core.database import AsyncSessionLocal
    from app.repositories.video_feed import VideoFeedRepository
    from app.services.stream_manager import get_stream_manager
    from app.utils.encryption import decrypt_rtsp_url
    from app.core.config import settings

    manager = get_stream_manager()
    await manager.start()

    # Load all ACTIVE feeds from DB
    async with AsyncSessionLocal() as session:
        repo = VideoFeedRepository(session)
        feeds = await repo.get_multi(
            filters=[],
            skip=0,
            limit=10000,
        )

    active_feeds = [f for f in feeds if f.status == "ACTIVE"]
    logger.info("Found %d active feeds in database", len(active_feeds))

    # Shard feeds across worker instances
    my_feeds = [
        f for i, f in enumerate(active_feeds)
        if i % WORKER_COUNT == WORKER_INDEX
    ]
    logger.info("Worker %d handling %d feeds", WORKER_INDEX, len(my_feeds))

    # Start ingestion for each assigned feed
    started: Set[str] = set()
    for feed in my_feeds:
        if len(started) >= SLOTS_PER_PROCESS:
            logger.warning("Slot limit reached (%d), skipping remaining feeds", SLOTS_PER_PROCESS)
            break
        try:
            rtsp_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
            ok = await manager.add_feed(
                feed_id=str(feed.id),
                rtsp_url=rtsp_url,
                priority=2,
                fps_ai=5,
                fps_display=25,
            )
            if ok:
                started.add(str(feed.id))
                logger.info("Started feed %s (%s)", feed.id, feed.name)
        except Exception as exc:
            logger.error("Failed to start feed %s: %s", feed.id, exc)

    logger.info("Stream worker ready — %d feeds active", len(started))

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _handle_signal(sig: int) -> None:
        logger.info("Received signal %d — shutting down", sig)
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    # Keep running until shutdown signal
    await stop_event.wait()

    logger.info("Stopping stream worker...")
    await manager.stop()
    logger.info("Stream worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
