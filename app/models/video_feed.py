"""Video Feed Model"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FeedType(str, PyEnum):
    """Video feed type enumeration"""

    FIXED_CAMERA = "FIXED_CAMERA"
    DRONE = "DRONE"
    BODY_CAM = "BODY_CAM"
    LEGACY_CCTV = "LEGACY_CCTV"
    IP_CAMERA = "IP_CAMERA"  # Network IP camera (ONVIF / RTSP)


class FeedStatus(str, PyEnum):
    """Video feed status enumeration"""

    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"


class VideoFeed(Base, UUIDMixin, TimestampMixin):
    """Video feed model for camera/drone stream management"""

    __tablename__ = "video_feeds"

    # Feed identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Feed name/identifier")

    # Feed type
    feed_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Feed type (FIXED_CAMERA, DRONE, BODY_CAM, LEGACY_CCTV)",
    )

    # Connection details (encrypted)
    rtsp_url_encrypted: Mapped[str] = mapped_column(
        Text, nullable=False, comment="AES-256 encrypted RTSP URL"
    )

    # Location information
    location_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Human-readable location name"
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 8), nullable=True, comment="GPS latitude coordinate"
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(11, 8), nullable=True, comment="GPS longitude coordinate"
    )

    # Zone assignment
    zone_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("security_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated security zone",
    )

    # Feed status
    status: Mapped[str] = mapped_column(
        String(20),
        default="OFFLINE",
        nullable=False,
        index=True,
        comment="Current feed status (ACTIVE, OFFLINE, DEGRADED, MAINTENANCE)",
    )

    # Stream metadata
    resolution: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Video resolution (e.g., 1920x1080)"
    )
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Frames per second")
    codec: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Video codec (e.g., h264)")

    # AI processing
    ai_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="AI processing enabled for this feed"
    )

    # Activity tracking
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last time feed was active"
    )

    # Relationships
    zone: Mapped["SecurityZone"] = relationship("SecurityZone", back_populates="feeds", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "feed_type IN ('FIXED_CAMERA', 'DRONE', 'BODY_CAM', 'LEGACY_CCTV', 'IP_CAMERA')",
            name="check_feed_type_valid",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'OFFLINE', 'DEGRADED', 'MAINTENANCE')",
            name="check_feed_status_valid",
        ),
        Index("idx_feeds_zone", "zone_id"),
        Index("idx_feeds_status", "status"),
        Index("idx_feeds_type", "feed_type"),
    )

    def encrypt_rtsp_url(self, plain_url: str, encryption_key: str) -> str:
        """
        Encrypt RTSP URL using AES-256-GCM.

        This method should be called before storing the URL.
        Implementation will be in app/utils/encryption.py

        Args:
            plain_url: Plain text RTSP URL
            encryption_key: Encryption key

        Returns:
            Encrypted URL as base64 string
        """
        # TODO: Implement in utils/encryption.py
        raise NotImplementedError("Encryption implementation pending")

    def decrypt_rtsp_url(self, encryption_key: str) -> str:
        """
        Decrypt RTSP URL using AES-256-GCM.

        This method should be called when retrieving the URL for use.
        Implementation will be in app/utils/encryption.py

        Args:
            encryption_key: Encryption key

        Returns:
            Decrypted plain text RTSP URL
        """
        # TODO: Implement in utils/encryption.py
        raise NotImplementedError("Decryption implementation pending")

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<VideoFeed(id={self.id}, name='{self.name}', "
            f"feed_type='{self.feed_type}', status='{self.status}')>"
        )
