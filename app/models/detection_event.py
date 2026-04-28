"""Detection Event Model (TimescaleDB Hypertable)"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, Numeric, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DetectionType(str, PyEnum):
    """Detection type enumeration"""

    FACE = "FACE"
    OBJECT = "OBJECT"
    VEHICLE = "VEHICLE"
    ANOMALY = "ANOMALY"
    ZONE_BREACH = "ZONE_BREACH"
    LICENSE_PLATE = "LICENSE_PLATE"
    WEAPON = "WEAPON"


class DetectionThreatLevel(str, PyEnum):
    """Detection threat level enumeration"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DetectionEvent(Base):
    """
    Detection event model for AI/ML detection results.
    
    This table is converted to a TimescaleDB hypertable for efficient time-series queries.
    The conversion happens in the Alembic migration using:
    SELECT create_hypertable('detection_events', 'frame_timestamp');
    """

    __tablename__ = "detection_events"

    # Composite primary key (id, frame_timestamp) for TimescaleDB
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()", nullable=False
    )
    frame_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, comment="Frame capture timestamp"
    )

    # Feed reference
    feed_id: Mapped[UUID] = mapped_column(
        ForeignKey("video_feeds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source video feed",
    )

    # Processing metadata
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Detection processing timestamp",
    )

    # Detection classification
    detection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Detection type (FACE, OBJECT, VEHICLE, ANOMALY, ZONE_BREACH)",
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, comment="Confidence score (0.0000 to 1.0000)"
    )

    # Bounding box and classification
    bounding_box: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Bounding box {x, y, w, h} as percentages (0.0-1.0)"
    )
    object_class: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Object class (e.g., person, weapon, bag, vehicle)"
    )

    # Person tracking
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tracked_persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated tracked person",
    )

    # Watchlist matching
    watchlist_match_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("watchlist_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Matched watchlist entry",
    )

    # Threat assessment
    threat_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Threat level (LOW, MEDIUM, HIGH, CRITICAL)"
    )

    # Operator classification
    operator_label: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Operator-assigned label (SUSPECT, CIVILIAN, FRIENDLY, UNKNOWN)"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Operator notes")

    # Frame snapshot
    frame_snapshot_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Encrypted MinIO storage path for frame snapshot"
    )

    # Relationships
    feed: Mapped["VideoFeed"] = relationship("VideoFeed", lazy="selectin")
    person: Mapped["TrackedPerson"] = relationship("TrackedPerson", lazy="selectin")
    watchlist_match: Mapped["WatchlistEntry"] = relationship("WatchlistEntry", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "detection_type IN ('FACE', 'OBJECT', 'VEHICLE', 'ANOMALY', 'ZONE_BREACH', 'LICENSE_PLATE', 'WEAPON')",
            name="check_detection_type_valid",
        ),
        CheckConstraint(
            "threat_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="check_detection_threat_level_valid",
        ),
        CheckConstraint(
            "operator_label IN ('SUSPECT', 'CIVILIAN', 'FRIENDLY', 'UNKNOWN')",
            name="check_detection_operator_label_valid",
        ),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="check_confidence_score_range"),
        # TimescaleDB optimized indexes
        Index("idx_detection_events_feed", "feed_id", "frame_timestamp"),
        Index("idx_detection_events_type", "detection_type"),
        Index("idx_detection_events_person", "person_id"),
        Index("idx_detection_events_watchlist", "watchlist_match_id"),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<DetectionEvent(id={self.id}, detection_type='{self.detection_type}', "
            f"confidence={self.confidence_score}, frame_timestamp={self.frame_timestamp})>"
        )
