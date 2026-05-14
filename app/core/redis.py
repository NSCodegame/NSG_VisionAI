"""
Redis connection pool and stream utilities for NSG VisionAI Platform.

Provides async Redis connections for:
  - Celery broker/backend
  - WebSocket pub/sub channels
  - Redis Streams (frame transport between ingester and ML workers)
  - Alert deduplication cache
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Connection pool singleton ──────────────────────────────────────────────────

_redis_pool: Optional[Redis] = None


async def get_redis() -> Redis:
    """Return the shared async Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=200,      # 100 feeds × 2 connections each
            socket_keepalive=True,
            socket_keepalive_options={
                "TCP_KEEPIDLE": 60,
                "TCP_KEEPINTVL": 10,
                "TCP_KEEPCNT": 3,
            },
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis connection pool closed")


# ── Redis Streams helpers ──────────────────────────────────────────────────────

STREAM_PREFIX = "nsg:stream:"
CONSUMER_GROUP = "ml_workers"


def feed_stream_key(feed_id: str) -> str:
    """Return the Redis Stream key for a given feed."""
    return f"{STREAM_PREFIX}{feed_id}"


async def create_consumer_group(redis: Redis, feed_id: str) -> None:
    """
    Create a consumer group on a feed stream.

    Creates the stream with MKSTREAM if it does not already exist, so workers
    can safely call this before any frames have been published.
    """
    key = feed_stream_key(feed_id)
    try:
        await redis.xgroup_create(key, CONSUMER_GROUP, id="0", mkstream=True)
        logger.debug("Consumer group created for feed %s", feed_id)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            # Group already exists — harmless
            pass
        else:
            raise


async def publish_frame(
    redis: Redis,
    feed_id: str,
    frame_bytes: bytes,
    timestamp_ms: int,
    extra: Optional[dict] = None,
) -> str:
    """
    Publish a raw video frame to the feed's Redis Stream.

    Args:
        redis: Async Redis client.
        feed_id: UUID string of the VideoFeed.
        frame_bytes: JPEG-encoded frame bytes.
        timestamp_ms: Unix timestamp in milliseconds.
        extra: Optional extra fields (e.g. fps, sequence number).

    Returns:
        Stream entry ID assigned by Redis.
    """
    key = feed_stream_key(feed_id)
    fields: dict[str, Any] = {
        "feed_id": feed_id,
        "timestamp_ms": timestamp_ms,
        "frame": frame_bytes,
    }
    if extra:
        for k, v in extra.items():
            fields[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)

    entry_id: str = await redis.xadd(key, fields, maxlen=200, approximate=True)
    return entry_id


async def read_frames(
    redis: Redis,
    feed_id: str,
    consumer_name: str,
    count: int = 4,
    block_ms: int = 1000,
) -> list[tuple[str, dict]]:
    """
    Read frames from the feed stream using consumer group semantics.

    Args:
        redis: Async Redis client.
        feed_id: UUID string of the VideoFeed.
        consumer_name: Unique consumer name (e.g. worker hostname + pid).
        count: Maximum number of messages to read per call.
        block_ms: Milliseconds to block waiting for new messages.

    Returns:
        List of (entry_id, fields_dict) tuples.
    """
    key = feed_stream_key(feed_id)
    try:
        results = await redis.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername=consumer_name,
            streams={key: ">"},
            count=count,
            block=block_ms,
        )
    except aioredis.ResponseError:
        # Stream or group may not exist yet
        return []

    messages: list[tuple[str, dict]] = []
    if results:
        for _stream, entries in results:
            for entry_id, fields in entries:
                messages.append((entry_id, fields))
    return messages


async def ack_frame(redis: Redis, feed_id: str, entry_id: str) -> None:
    """Acknowledge a processed frame entry in the consumer group."""
    key = feed_stream_key(feed_id)
    await redis.xack(key, CONSUMER_GROUP, entry_id)


# ── Pub/Sub helpers (WebSocket broadcast) ─────────────────────────────────────

PUBSUB_ALERTS = "nsg:pubsub:alerts"
PUBSUB_MAP = "nsg:pubsub:map"
PUBSUB_HEALTH = "nsg:pubsub:health"


def detection_pubsub_channel(feed_id: str) -> str:
    """Return the pub/sub channel for detection events on a specific feed."""
    return f"nsg:pubsub:detections:{feed_id}"


async def publish_message(redis: Redis, channel: str, payload: dict) -> None:
    """Publish a JSON message to a Redis pub/sub channel."""
    await redis.publish(channel, json.dumps(payload, default=str))


# ── Alert deduplication cache ──────────────────────────────────────────────────

DEDUP_PREFIX = "nsg:dedup:"


async def check_dedup(
    redis: Redis,
    feed_id: str,
    object_class: str,
    bbox_center: tuple[float, float],
    window_seconds: int = 30,
) -> bool:
    """
    Check whether a similar alert was already generated within the window.

    Returns True if duplicate (should suppress), False if new alert.
    Uses a coarse grid bucket (0.05 coordinate resolution) as the dedup key.
    """
    bx = round(bbox_center[0] / 0.05) * 0.05
    by = round(bbox_center[1] / 0.05) * 0.05
    key = f"{DEDUP_PREFIX}{feed_id}:{object_class}:{bx:.2f}:{by:.2f}"
    exists = await redis.exists(key)
    if not exists:
        await redis.setex(key, window_seconds, "1")
    return bool(exists)


# ── Simple key-value cache helpers ────────────────────────────────────────────

async def set_cache(redis: Redis, key: str, value: Any, ttl: int = 30) -> None:
    """Set a JSON-serialisable value in Redis with TTL."""
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def get_cache(redis: Redis, key: str) -> Optional[Any]:
    """Get a cached value from Redis, returning None if missing."""
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)
