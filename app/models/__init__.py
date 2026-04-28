"""Database models"""
from app.models.alert import Alert, AlertPriority, AlertStatus, AlertType
from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.detection_event import DetectionEvent, DetectionThreatLevel, DetectionType
from app.models.ml_model import MLModel, ModelFramework, ModelType
from app.models.report import (
    ForensicJob,
    ForensicJobStatus,
    ForensicJobType,
    Report,
    ReportClassification,
    ReportStatus,
    ReportType,
)
from app.models.security_zone import SecurityZone, ThreatLevel, ZoneType
from app.models.tracked_person import OperatorLabel, TrackedPerson
from app.models.user import User, UserRole
from app.models.video_feed import FeedStatus, FeedType, VideoFeed
from app.models.video_segment import VideoSegment
from app.models.watchlist_entry import ThreatCategory, WatchlistEntry, WatchlistStatus

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # User
    "User",
    "UserRole",
    # Security Zone
    "SecurityZone",
    "ZoneType",
    "ThreatLevel",
    # Video Feed
    "VideoFeed",
    "FeedType",
    "FeedStatus",
    # Watchlist
    "WatchlistEntry",
    "ThreatCategory",
    "WatchlistStatus",
    # Tracked Person
    "TrackedPerson",
    "OperatorLabel",
    # Detection Event
    "DetectionEvent",
    "DetectionType",
    "DetectionThreatLevel",
    # Alert
    "Alert",
    "AlertType",
    "AlertPriority",
    "AlertStatus",
    # Video Segment
    "VideoSegment",
    # ML Model
    "MLModel",
    "ModelType",
    "ModelFramework",
    # Audit Log
    "AuditLog",
    # Report
    "Report",
    "ReportType",
    "ReportClassification",
    "ReportStatus",
    # Forensic Job
    "ForensicJob",
    "ForensicJobType",
    "ForensicJobStatus",
]
