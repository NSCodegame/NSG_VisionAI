"""Watchlist Entry Model"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ThreatCategory(str, PyEnum):
    """Threat category enumeration"""

    KNOWN_TERRORIST = "KNOWN_TERRORIST"
    SUSPECT = "SUSPECT"
    POI = "POI"  # Person of Interest
    BANNED = "BANNED"


class WatchlistStatus(str, PyEnum):
    """Watchlist entry status enumeration"""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


class WatchlistEntry(Base, UUIDMixin):
    """Watchlist entry model for person of interest tracking"""

    __tablename__ = "watchlist_entries"

    # Person identification (may be unknown)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Person name (may be unknown)")
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Known alias")

    # Threat classification
    threat_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Threat category (KNOWN_TERRORIST, SUSPECT, POI, BANNED)",
    )

    # Additional information
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Description and notes")
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Nationality")
    known_associates: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Known associates")

    # Face data
    face_images: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Array of MinIO storage paths for face images"
    )
    face_embedding: Mapped[Any] = mapped_column(
        Vector(512), nullable=True, comment="512-dimensional face embedding for similarity search"
    )

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING_APPROVAL",
        nullable=False,
        index=True,
        comment="Entry status (PENDING_APPROVAL, ACTIVE, DEACTIVATED)",
    )
    source_agency: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Source intelligence agency"
    )

    # User tracking
    added_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who added this entry",
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="User who approved this entry (COMMANDER+)",
    )

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()", comment="Entry creation timestamp"
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Entry approval timestamp"
    )

    # Relationships
    added_by_user: Mapped["User"] = relationship("User", foreign_keys=[added_by], lazy="selectin")
    approved_by_user: Mapped["User"] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    tracked_persons: Mapped[list["TrackedPerson"]] = relationship(
        "TrackedPerson", back_populates="watchlist_entry", lazy="selectin"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "threat_category IN ('KNOWN_TERRORIST', 'SUSPECT', 'POI', 'BANNED')",
            name="check_threat_category_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING_APPROVAL', 'ACTIVE', 'DEACTIVATED')",
            name="check_watchlist_status_valid",
        ),
        Index("idx_watchlist_status", "status"),
        # pgvector ivfflat index for fast similarity search
        Index(
            "idx_watchlist_face_embedding",
            "face_embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"face_embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<WatchlistEntry(id={self.id}, name='{self.name}', "
            f"threat_category='{self.threat_category}', status='{self.status}')>"
        )
