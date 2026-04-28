"""Video Segment Model"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class VideoSegment(Base, UUIDMixin):
    """Video segment model for archival index"""

    __tablename__ = "video_segments"

    # Feed reference
    feed_id: Mapped[UUID] = mapped_column(
        ForeignKey("video_feeds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source video feed",
    )

    # Temporal boundaries
    start_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, comment="Segment start timestamp"
    )
    end_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Segment end timestamp"
    )

    # Storage details
    storage_path: Mapped[str] = mapped_column(
        Text, nullable=False, comment="MinIO storage path (encrypted)"
    )
    encryption_key_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="Reference to key management system for AES-256-GCM encryption",
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="File size in bytes"
    )

    # Retention policy
    has_flagged_events: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether segment contains flagged events (permanent retention if true)",
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Retention expiration timestamp (NULL for permanent retention)",
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()", comment="Segment creation timestamp"
    )

    # Relationships
    feed: Mapped["VideoFeed"] = relationship("VideoFeed", lazy="selectin")

    # Table constraints
    __table_args__ = (
        Index("idx_video_segments_feed_start", "feed_id", "start_timestamp"),
        Index("idx_video_segments_retention", "retention_until"),
    )

    @property
    def is_permanent(self) -> bool:
        """Check if segment has permanent retention"""
        return self.retention_until is None or self.has_flagged_events

    @property
    def is_expired(self) -> bool:
        """Check if segment retention has expired"""
        if self.is_permanent:
            return False
        if self.retention_until is None:
            return False
        return datetime.now(self.retention_until.tzinfo) > self.retention_until

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<VideoSegment(id={self.id}, feed_id={self.feed_id}, "
            f"start={self.start_timestamp}, has_flagged_events={self.has_flagged_events})>"
        )
