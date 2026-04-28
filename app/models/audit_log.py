"""Audit Log Model (Immutable)"""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Index, JSON, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AuditLog(Base, UUIDMixin):
    """
    Audit log model for immutable tracking of all user actions.
    
    IMPORTANT: This table is immutable at the database level.
    UPDATE and DELETE operations are blocked by database rules:
    - CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
    - CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
    
    These rules are created in the Alembic migration.
    """

    __tablename__ = "audit_logs"

    # User reference
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who performed the action (NULL for system actions)",
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action performed (e.g., ALERT_ACKNOWLEDGED, VIDEO_EXPORTED)",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Resource type (e.g., ALERT, VIDEO_SEGMENT, USER)",
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True, comment="Resource ID"
    )

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="Client IP address"
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Client user agent string"
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, comment="Session ID"
    )

    # Detailed payload
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Full before/after payload and additional context"
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        index=True,
        comment="Action timestamp",
    )

    # Table constraints
    __table_args__ = (
        Index("idx_audit_logs_user", "user_id", "timestamp"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', "
            f"resource_type='{self.resource_type}', timestamp={self.timestamp})>"
        )
