"""
Celery Application Configuration — Production distributed AI workers

Worker topology for 100+ feeds:
  - detection_queue  → GPU workers (1 per GPU, batch processing)
  - face_queue       → CPU workers (4 concurrent, DeepFace)
  - tracking_queue   → CPU workers (2 concurrent, ByteTrack)
  - anomaly_queue    → CPU workers (2 concurrent, LSTM)
  - alert_queue      → CPU workers (4 concurrent, fast)
  - archival_queue   → I/O workers (2 concurrent, FFmpeg/MinIO)
  - recording_queue  → I/O workers (2 concurrent, clip extraction)

Scale with: celery -A app.core.celery_app worker -Q detection_queue --concurrency=1 -P solo
"""

from celery import Celery
from kombu import Queue, Exchange

from app.core.config import settings

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
        "app.tasks.recording_tasks",
        "app.tasks.cleanup_tasks",
    ],
)

# ── General Configuration ──────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,   # One task at a time per worker slot
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,

    # Result backend
    result_expires=3600,

    # Rate limiting — prevent Redis overload
    task_default_rate_limit="100/s",

    # Timeouts
    task_soft_time_limit=30,        # Warn after 30s
    task_time_limit=60,             # Kill after 60s (prevents zombie workers)

    # Worker optimizations
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (memory leak prevention)
    worker_disable_rate_limits=False,
)

# ── Queue Configuration ────────────────────────────────────────────────────────

ml_exchange       = Exchange("ml_exchange",       type="direct")
alert_exchange    = Exchange("alert_exchange",    type="direct")
archival_exchange = Exchange("archival_exchange", type="direct")
recording_exchange = Exchange("recording_exchange", type="direct")

celery_app.conf.task_queues = (
    # GPU queue — high priority, low concurrency (1 per GPU)
    Queue("detection_queue",  ml_exchange,        routing_key="ml.detection",  queue_arguments={"x-max-priority": 10}),
    Queue("face_queue",       ml_exchange,        routing_key="ml.face"),
    Queue("tracking_queue",   ml_exchange,        routing_key="ml.tracking"),
    Queue("anomaly_queue",    ml_exchange,        routing_key="ml.anomaly"),
    Queue("alert_queue",      alert_exchange,     routing_key="alert.process", queue_arguments={"x-max-priority": 10}),
    Queue("archival_queue",   archival_exchange,  routing_key="video.archive"),
    Queue("recording_queue",  recording_exchange, routing_key="video.record"),
)

celery_app.conf.task_routes = {
    "app.tasks.detection_tasks.*":  {"queue": "detection_queue",  "routing_key": "ml.detection"},
    "app.tasks.face_tasks.*":       {"queue": "face_queue",        "routing_key": "ml.face"},
    "app.tasks.tracking_tasks.*":   {"queue": "tracking_queue",    "routing_key": "ml.tracking"},
    "app.tasks.anomaly_tasks.*":    {"queue": "anomaly_queue",     "routing_key": "ml.anomaly"},
    "app.tasks.alert_tasks.*":      {"queue": "alert_queue",       "routing_key": "alert.process"},
    "app.tasks.archival_tasks.*":   {"queue": "archival_queue",    "routing_key": "video.archive"},
    "app.tasks.recording_tasks.*":  {"queue": "recording_queue",   "routing_key": "video.record"},
}

# ── Celery Beat (Scheduled Tasks) ──────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "apply-retention-policy": {
        "task": "app.tasks.archival_tasks.apply_retention_policy",
        "schedule": 3600.0,
    },
    "cleanup-old-segments": {
        "task": "app.tasks.recording_tasks.cleanup_all_segments",
        "schedule": 1800.0,   # Every 30 minutes
    },
    "system-health-check": {
        "task": "app.tasks.cleanup_tasks.check_system_health",
        "schedule": 60.0,
    },
}
