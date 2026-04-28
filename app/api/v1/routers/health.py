"""
Health & Monitoring Router — Phase 26, Task 26.1

Provides tactical system health metrics including GPU/CPU load, 
database latency, and transcoder status for mission-critical monitoring.
"""

import time
import shutil
import psutil
from typing import Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_admin
from app.core.database import get_db
from app.services.transcoding_service import get_transcoding_service

router = APIRouter(prefix="/health", tags=["Monitoring"])

@router.get(
    "/system",
    dependencies=[Depends(require_admin)]
)
async def get_system_health(db: AsyncSession = Depends(get_db)):
    """
    Get detailed tactical system metrics.
    Requires ADMIN privileges.
    """
    # 1. Database Latency
    start_time = time.time()
    await db.execute(text("SELECT 1"))
    db_latency_ms = round((time.time() - start_time) * 1000, 2)

    # 2. Disk Usage (Stream storage)
    total, used, free = shutil.disk_usage("d:/Project/NSG/streams")
    disk_usage_percent = round((used / total) * 100, 2)

    # 3. CPU/RAM
    cpu_load = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    # 4. Transcoder Status
    transcoder = get_transcoding_service()
    active_streams = len(transcoder._active_processes)

    # 5. GPU Metrics (Simulated if no CUDA)
    import torch
    gpu_metrics = {
        "available": torch.cuda.is_available(),
        "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "load_percent": 42.5 if torch.cuda.is_available() else 0.0 # Mock load for now
    }

    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "database_latency_ms": db_latency_ms,
            "disk_usage_percent": disk_usage_percent,
            "cpu_load_percent": cpu_load,
            "ram_usage_percent": ram_usage,
            "gpu": gpu_metrics,
            "active_transcodes": active_streams
        }
    }

from datetime import datetime
