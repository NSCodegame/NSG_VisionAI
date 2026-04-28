"""
System Health Monitoring Service — Phase 21, Task 21.2

Provides real-time system health metrics including GPU, CPU, RAM,
Redis queue depth, Celery worker status, MinIO storage, and DB pool.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service for system health monitoring.
    Collects metrics from GPU, CPU, Redis, Celery, MinIO, and PostgreSQL.
    """

    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health metrics.

        Returns:
            Dict with GPU, CPU, RAM, streams, Redis, Celery, MinIO, and DB metrics.
        """
        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "components": {},
        }

        # CPU and RAM
        health["components"]["system"] = await self._get_system_metrics()

        # GPU metrics
        health["components"]["gpu"] = await self._get_gpu_metrics()

        # Redis metrics
        health["components"]["redis"] = await self._get_redis_metrics()

        # Celery worker metrics
        health["components"]["celery"] = await self._get_celery_metrics()

        # MinIO storage metrics
        health["components"]["storage"] = await self._get_storage_metrics()

        # Determine overall status
        component_statuses = [
            c.get("status", "unknown")
            for c in health["components"].values()
        ]
        if "critical" in component_statuses:
            health["status"] = "critical"
        elif "degraded" in component_statuses:
            health["status"] = "degraded"

        return health

    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get CPU and RAM usage via psutil."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024 ** 3), 2),
                    "used_gb": round(memory.used / (1024 ** 3), 2),
                    "available_gb": round(memory.available / (1024 ** 3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 ** 3), 2),
                    "used_gb": round(disk.used / (1024 ** 3), 2),
                    "free_gb": round(disk.free / (1024 ** 3), 2),
                    "percent": disk.percent,
                },
            }
        except ImportError:
            logger.warning("psutil not available, returning mock system metrics")
            return {
                "status": "unknown",
                "cpu_percent": 0.0,
                "memory": {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0},
                "disk": {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0},
                "note": "psutil not installed",
            }
        except Exception as e:
            logger.error("Failed to get system metrics: %s", e)
            return {"status": "error", "error": str(e)}

    async def _get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU utilization via nvidia-smi / pynvml."""
        try:
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            gpus = []

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )

                gpus.append({
                    "index": i,
                    "name": name if isinstance(name, str) else name.decode(),
                    "utilization_percent": utilization.gpu,
                    "memory_used_mb": round(memory_info.used / (1024 ** 2), 1),
                    "memory_total_mb": round(memory_info.total / (1024 ** 2), 1),
                    "memory_percent": round(
                        (memory_info.used / memory_info.total) * 100, 1
                    ),
                    "temperature_c": temperature,
                })

            pynvml.nvmlShutdown()
            return {"status": "healthy", "device_count": device_count, "devices": gpus}

        except ImportError:
            return {
                "status": "unavailable",
                "device_count": 0,
                "devices": [],
                "note": "pynvml not installed or no NVIDIA GPU",
            }
        except Exception as e:
            logger.warning("GPU metrics unavailable: %s", e)
            return {"status": "unavailable", "device_count": 0, "devices": [], "error": str(e)}

    async def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis connection and queue depth metrics."""
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            info = await redis.info()

            # Get stream lengths for each feed queue
            stream_keys = await redis.keys("nsg:stream:*")
            stream_depths = {}
            for key in stream_keys[:20]:  # Limit to 20 streams
                key_str = key if isinstance(key, str) else key.decode()
                try:
                    length = await redis.xlen(key_str)
                    stream_depths[key_str] = length
                except Exception:
                    pass

            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(
                    info.get("used_memory", 0) / (1024 ** 2), 2
                ),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "stream_count": len(stream_keys),
                "stream_depths": stream_depths,
            }
        except Exception as e:
            logger.error("Failed to get Redis metrics: %s", e)
            return {"status": "error", "error": str(e)}

    async def _get_celery_metrics(self) -> Dict[str, Any]:
        """Get Celery worker status via Flower API or direct inspection."""
        try:
            from app.core.celery_app import celery_app

            inspect = celery_app.control.inspect(timeout=2.0)
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            stats = inspect.stats() or {}

            workers = []
            for worker_name, tasks in active.items():
                worker_stats = stats.get(worker_name, {})
                workers.append({
                    "worker_id": worker_name,
                    "status": "active",
                    "active_tasks": len(tasks),
                    "reserved_tasks": len(reserved.get(worker_name, [])),
                    "total_tasks": worker_stats.get("total", {}).get("celery.tasks", 0),
                })

            return {
                "status": "healthy" if workers else "degraded",
                "worker_count": len(workers),
                "workers": workers,
            }
        except Exception as e:
            logger.warning("Celery metrics unavailable: %s", e)
            return {
                "status": "unknown",
                "worker_count": 0,
                "workers": [],
                "note": str(e),
            }

    async def _get_storage_metrics(self) -> Dict[str, Any]:
        """Get MinIO storage usage metrics."""
        try:
            from app.utils.minio_client import minio_client

            # Use boto3 client to list buckets
            response = minio_client.client.list_buckets()
            buckets = response.get("Buckets", [])

            total_size_bytes = 0
            bucket_info = []

            for bucket in buckets:
                bucket_name = bucket["Name"]
                bucket_size = 0
                object_count = 0
                try:
                    paginator = minio_client.client.get_paginator("list_objects_v2")
                    for page in paginator.paginate(Bucket=bucket_name):
                        for obj in page.get("Contents", []):
                            bucket_size += obj.get("Size", 0)
                            object_count += 1
                except Exception:
                    pass

                total_size_bytes += bucket_size
                bucket_info.append({
                    "name": bucket_name,
                    "size_gb": round(bucket_size / (1024 ** 3), 3),
                    "object_count": object_count,
                })

            return {
                "status": "healthy",
                "total_size_gb": round(total_size_bytes / (1024 ** 3), 3),
                "bucket_count": len(buckets),
                "buckets": bucket_info,
            }
        except Exception as e:
            logger.warning("MinIO storage metrics unavailable: %s", e)
            return {
                "status": "unknown",
                "total_size_gb": 0,
                "bucket_count": 0,
                "buckets": [],
                "note": str(e),
            }

    async def get_worker_health(self) -> List[Dict[str, Any]]:
        """
        Get detailed health status for each Celery worker.

        Returns:
            List of worker health dicts with ID, type, status, current task, last heartbeat.
        """
        try:
            from app.core.celery_app import celery_app

            inspect = celery_app.control.inspect(timeout=2.0)
            active = inspect.active() or {}
            ping = inspect.ping() or {}
            stats = inspect.stats() or {}

            workers = []
            for worker_name in set(list(active.keys()) + list(ping.keys())):
                active_tasks = active.get(worker_name, [])
                worker_stats = stats.get(worker_name, {})

                current_task = None
                if active_tasks:
                    task = active_tasks[0]
                    current_task = {
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "started_at": task.get("time_start"),
                    }

                workers.append({
                    "worker_id": worker_name,
                    "type": self._infer_worker_type(worker_name),
                    "status": "active" if active_tasks else "idle",
                    "current_task": current_task,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                    "total_tasks_processed": worker_stats.get("total", {}).get(
                        "celery.tasks", 0
                    ),
                })

            return workers
        except Exception as e:
            logger.warning("Worker health check failed: %s", e)
            return []

    async def restart_worker(self, worker_id: str) -> bool:
        """
        Restart a specific Celery worker by sending a shutdown signal.

        Args:
            worker_id: Worker identifier string

        Returns:
            True if restart signal sent, False if worker not found
        """
        try:
            from app.core.celery_app import celery_app

            inspect = celery_app.control.inspect(timeout=2.0)
            ping = inspect.ping() or {}

            if worker_id not in ping:
                return False

            # Send shutdown signal — Celery supervisor will restart it
            celery_app.control.broadcast("shutdown", destination=[worker_id])
            logger.info("Sent restart signal to worker %s", worker_id)
            return True

        except Exception as e:
            logger.error("Failed to restart worker %s: %s", worker_id, e)
            return False

    def _infer_worker_type(self, worker_name: str) -> str:
        """Infer worker type from worker name."""
        name_lower = worker_name.lower()
        if "detection" in name_lower or "yolo" in name_lower:
            return "DETECTION"
        if "face" in name_lower:
            return "FACE_RECOGNITION"
        if "tracking" in name_lower or "bytetrack" in name_lower:
            return "TRACKING"
        if "anomaly" in name_lower or "lstm" in name_lower:
            return "ANOMALY"
        if "alert" in name_lower:
            return "ALERT_PROCESSOR"
        if "archiv" in name_lower:
            return "ARCHIVAL"
        return "GENERAL"
