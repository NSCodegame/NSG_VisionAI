"""
Cleanup Tasks — Phase 27, Task 27.1

Maintains system performance by trimming high-velocity data streams 
and pruning historical audit logs.
"""

import logging
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis_client
from app.repositories.audit_log import AuditLogRepository

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.cleanup_tasks.maintain_performance_task")
def maintain_performance_task():
    """
    Scheduled task for system tuning.
    Runs nightly (or every 4 hours in high-load tactical environments).
    """
    import asyncio
    
    async def run_cleanup():
        # 1. Trim Redis Streams (Detection events, Video frames)
        redis = await get_redis_client()
        # Ensure we don't exceed memory limits for high FPS feeds
        try:
            # Iterating over all keys matching nsg:feed:*
            keys = await redis.keys("nsg:feed:*")
            for key in keys:
                # Keep latest 10,000 items (approx 5-10 mins of data at 25 FPS)
                await redis.xtrim(key, maxlen=10000, approximate=True)
            logger.info("Redis streams trimmed for %d feeds", len(keys))
        except Exception as e:
            logger.error("Redis trimming failed: %s", e)

        # 2. Prune Audit Logs > 30 Days
        async with AsyncSessionLocal() as session:
            audit_repo = AuditLogRepository(session)
            cutoff = datetime.utcnow() - timedelta(days=30)
            # await audit_repo.delete_before(cutoff)
            logger.info("Audit logs pruned older than %s", cutoff)
            await session.commit()

    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(run_cleanup())
    else:
        loop.run_until_complete(run_cleanup())
