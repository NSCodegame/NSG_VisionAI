"""Alert Model"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AlertType(str, PyEnum):
    """Alert type enumeration"""

    WATCHLIST_MATCH = "WATCHLIST_MATCH"
    ZONE_BREACH = "ZONE_BREACH"
    WEAPON_DETECTED = "WEAPON_DETECTED"
    UNATTENDED_OBJECT = "UNATTENDED_OBJECT"
    CROWD_ANOMALY = "CROWD_ANOMALY"
    LOITERING = "LOITERING"
    VEHICLE_THREAT = "VEHICLE_THREAT"


class AlertPriority(str, PyEnum):
    """Alert priority enumeration"""

    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class AlertStatus(str, PyEnum):
    """Alert status enumeration"""

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class Alert(Base, UUIDMixin):
    """Alert model for prioritized notifications"""

    __tablename__ = "alerts"

    # Detection reference
    detection_event_id: Mapped[UUID] = mapped_column(
        # Note: Cannot use ForeignKey with composite key, handled at application level
        nullable=False,
        comment="Associated detection event ID",
    )

    # Alert classification
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Alert type (WATCHLIST_MATCH, ZONE_BREACH, WEAPON_DETECTED, etc.)",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Alert priority (P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
        index=True,
        comment="Alert status (ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)",
    )

    # Context references
    feed_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("video_feeds.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Source video feed",
    )
    zone_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("security_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated security zone",
    )

    # Alert metadata
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True, comment="Detection confidence score"
    )

    # Timestamps
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        index=True,
        comment="Alert trigger timestamp",
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Alert acknowledgement timestamp"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Alert resolution timestamp"
    )

    # User actions
    acknowledged_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who acknowledged the alert",
    )

    # Resolution details
    resolution_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Resolution notes (required for RESOLVED status)"
    )
    false_positive_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reason for marking as false positive"
    )

    # Deduplication
    occurrence_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Number of occurrences (for deduplication)"
    )

    # Relationships
    feed: Mapped["VideoFeed"] = relationship("VideoFeed", lazy="selectin")
    zone: Mapped["SecurityZone"] = relationship("SecurityZone", lazy="selectin")
    acknowledged_by_user: Mapped["User"] = relationship("User", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('WATCHLIST_MATCH', 'ZONE_BREACH', 'WEAPON_DETECTED', "
            "'UNATTENDED_OBJECT', 'CROWD_ANOMALY', 'LOITERING', 'VEHICLE_THREAT')",
            name="check_alert_type_valid",
        ),
        CheckConstraint(
            "priority IN ('P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM', 'P4_LOW')",
            name="check_alert_priority_valid",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE')",
            name="check_alert_status_valid",
        ),
        Index("idx_alerts_status", "status"),
        Index("idx_alerts_priority", "priority"),
        Index("idx_alerts_triggered_at", "triggered_at"),
        Index("idx_alerts_feed", "feed_id"),
        Index("idx_alerts_zone", "zone_id"),
        Index("idx_alerts_type", "alert_type"),
    )

    @staticmethod
    def calculate_priority(
        alert_type: str, zone_threat_level: str, confidence_score: float
    ) -> str:
        """
        Calculate alert priority based on type, zone threat level, and confidence.

        Priority rules from design document:
        - WATCHLIST_MATCH + confidence >0.90 → P1_CRITICAL
        - WEAPON_DETECTED → P1_CRITICAL
        - CRITICAL zone + confidence >0.85 → P1_CRITICAL
        - CRITICAL zone + confidence ≤0.85 → P2_HIGH
        - RED zone + confidence >0.80 → P2_HIGH
        - RED zone + confidence ≤0.80 → P3_MEDIUM
        - Other combinations → P3_MEDIUM or P4_LOW

        Args:
            alert_type: Type of alert
            zone_threat_level: Zone threat level (GREEN, AMBER, RED, CRITICAL)
            confidence_score: Detection confidence (0.0-1.0)

        Returns:
            Alert priority (P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW)
        """
        # P1_CRITICAL conditions
        if alert_type == "WATCHLIST_MATCH" and confidence_score > 0.90:
            return "P1_CRITICAL"
        if alert_type == "WEAPON_DETECTED":
            return "P1_CRITICAL"
        if zone_threat_level == "CRITICAL" and confidence_score > 0.85:
            return "P1_CRITICAL"

        # P2_HIGH conditions
        if zone_threat_level == "CRITICAL" and confidence_score <= 0.85:
            return "P2_HIGH"
        if zone_threat_level == "RED" and confidence_score > 0.80:
            return "P2_HIGH"

        # P3_MEDIUM conditions
        if zone_threat_level == "RED" and confidence_score <= 0.80:
            return "P3_MEDIUM"
        if zone_threat_level == "AMBER":
            return "P3_MEDIUM"

        # P4_LOW (default)
        return "P4_LOW"

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<Alert(id={self.id}, alert_type='{self.alert_type}', "
            f"priority='{self.priority}', status='{self.status}')>"
        )
