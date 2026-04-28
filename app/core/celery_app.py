"""
Celery Application Configuration — Phase 9

Defines the Celery application for distributed AI/ML processing,
alert generation, and video archival.
"""

from celery import Celery
from kombu import Queue, Exchange

from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "nsg_visionai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.detection_tasks",
        "app.tasks.face_tasks",
        "app.tasks.tracking_tasks",
        "app.tasks.anomaly_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.archival_tasks",
    ]
)

# ── General Configuration ──────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Performance & Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Maintain frame order per worker
    task_reject_on_worker_lost=True,
    
    # Result Backend Settings
    result_expires=3600,  # 1 hour
)

# ── Queue Configuration ────────────────────────────────────────────────────────

# Define Exchanges
ml_exchange = Exchange("ml_exchange", type="direct")
alert_exchange = Exchange("alert_exchange", type="direct")
archival_exchange = Exchange("archival_exchange", type="direct")

# Define Queues
celery_app.conf.task_queues = (
    Queue("detection_queue", ml_exchange, routing_key="ml.detection"),
    Queue("face_queue", ml_exchange, routing_key="ml.face"),
    Queue("tracking_queue", ml_exchange, routing_key="ml.tracking"),
    Queue("anomaly_queue", ml_exchange, routing_key="ml.anomaly"),
    Queue("alert_queue", alert_exchange, routing_key="alert.process"),
    Queue("archival_queue", archival_exchange, routing_key="video.archive"),
)

# ── Task Routing ───────────────────────────────────────────────────────────────

celery_app.conf.task_routes = {
    "app.tasks.detection_tasks.*": {"queue": "detection_queue", "routing_key": "ml.detection"},
    "app.tasks.face_tasks.*": {"queue": "face_queue", "routing_key": "ml.face"},
    "app.tasks.tracking_tasks.*": {"queue": "tracking_queue", "routing_key": "ml.tracking"},
    "app.tasks.anomaly_tasks.*": {"queue": "anomaly_queue", "routing_key": "ml.anomaly"},
    "app.tasks.alert_tasks.*": {"queue": "alert_queue", "routing_key": "alert.process"},
    "app.tasks.archival_tasks.*": {"queue": "archival_queue", "routing_key": "video.archive"},
}

# ── Celery Beat (Scheduled Tasks) ──────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "apply-retention-policy": {
        "task": "app.tasks.archival_tasks.apply_retention_policy",
        "schedule": 3600.0,  # Every hour
    },
    "system-health-check": {
        "task": "app.tasks.admin_tasks.check_system_health",
        "schedule": 60.0,  # Every minute
    },
}
