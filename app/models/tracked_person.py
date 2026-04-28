"""Tracked Person Model"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class OperatorLabel(str, PyEnum):
    """Operator-assigned label for tracked person"""

    SUSPECT = "SUSPECT"
    CIVILIAN = "CIVILIAN"
    FRIENDLY = "FRIENDLY"
    UNKNOWN = "UNKNOWN"


class TrackedPerson(Base, UUIDMixin, TimestampMixin):
    """Tracked person model for multi-object person tracking across feeds"""

    __tablename__ = "tracked_persons"

    # ByteTrack tracking ID
    track_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="ByteTrack internal tracking ID"
    )

    # Temporal tracking
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="First detection timestamp"
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Last detection timestamp"
    )

    # Feed tracking
    feed_ids_seen: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Array of feed UUIDs where person was detected"
    )

    # Cross-camera re-identification
    face_embedding: Mapped[Any] = mapped_column(
        Vector(512), nullable=True, comment="512-dimensional face embedding"
    )
    reid_embedding: Mapped[Any] = mapped_column(
        Vector(512), nullable=True, comment="512-dimensional body feature embedding for cross-camera linking"
    )

    # Master/Parent identity for cross-camera continuity
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tracked_persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent identity for linking tracks across non-overlapping views"
    )

    # Operator classification
    operator_label: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Operator-assigned label (SUSPECT, CIVILIAN, FRIENDLY, UNKNOWN)",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Operator notes")

    # Watchlist matching
    watchlist_match: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Whether person matches watchlist"
    )
    watchlist_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("watchlist_entries.id", ondelete="SET NULL"),
        nullable=True,
        comment="Matched watchlist entry",
    )

    # Movement trajectory
    trajectory: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of {feed_id, timestamp, position: {x, y}} tracking movement",
    )

    # Relationships
    watchlist_entry: Mapped["WatchlistEntry"] = relationship(
        "WatchlistEntry", back_populates="tracked_persons", lazy="selectin"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "operator_label IN ('SUSPECT', 'CIVILIAN', 'FRIENDLY', 'UNKNOWN')",
            name="check_operator_label_valid",
        ),
        Index("idx_tracked_persons_track_id", "track_id"),
        Index("idx_tracked_persons_watchlist_match", "watchlist_match"),
        Index("idx_tracked_persons_last_seen", "last_seen_at"),
    )

    @staticmethod
    def validate_trajectory(trajectory: dict[str, Any]) -> bool:
        """
        Validate trajectory data structure and timestamp monotonicity.

        Expected format:
        {
            "points": [
                {
                    "feed_id": "uuid",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "position": {"x": 0.5, "y": 0.3}
                },
                ...
            ]
        }

        Timestamps must be monotonically increasing.

        Args:
            trajectory: Trajectory data dictionary

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(trajectory, dict):
            return False

        points = trajectory.get("points")
        if not isinstance(points, list):
            return False

        prev_timestamp = None
        for point in points:
            if not isinstance(point, dict):
                return False

            # Check required fields
            if "feed_id" not in point or "timestamp" not in point or "position" not in point:
                return False

            # Validate position
            position = point["position"]
            if not isinstance(position, dict) or "x" not in position or "y" not in position:
                return False

            # Check timestamp monotonicity
            try:
                current_timestamp = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                if prev_timestamp and current_timestamp <= prev_timestamp:
                    return False
                prev_timestamp = current_timestamp
            except (ValueError, AttributeError):
                return False

        return True

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<TrackedPerson(id={self.id}, track_id='{self.track_id}', "
            f"operator_label='{self.operator_label}', watchlist_match={self.watchlist_match})>"
        )
