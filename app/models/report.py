"""Report and Forensic Job Models"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ReportType(str, PyEnum):
    """Report type enumeration"""

    INCIDENT_REPORT = "INCIDENT_REPORT"
    PERSON_REPORT = "PERSON_REPORT"
    ZONE_ACTIVITY = "ZONE_ACTIVITY"
    OPERATION_SUMMARY = "OPERATION_SUMMARY"
    FORENSIC_TIMELINE = "FORENSIC_TIMELINE"


class ReportClassification(str, PyEnum):
    """Report classification enumeration"""

    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"


class ReportStatus(str, PyEnum):
    """Report generation status enumeration"""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Report(Base, UUIDMixin):
    """Report model for intelligence report generation"""

    __tablename__ = "reports"

    # Report metadata
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Report type (INCIDENT_REPORT, PERSON_REPORT, ZONE_ACTIVITY, etc.)",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Report title")
    classification: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Security classification (RESTRICTED, CONFIDENTIAL, SECRET)",
    )

    # Report content
    detection_event_ids: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Array of detection event UUIDs included in report"
    )

    # Generation tracking
    generated_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who generated the report",
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        index=True,
        comment="Report generation timestamp",
    )

    # Output file
    file_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="PDF storage path in MinIO"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
        comment="Report generation status (PENDING, COMPLETED, FAILED)",
    )

    # Relationships
    generated_by_user: Mapped["User"] = relationship("User", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('INCIDENT_REPORT', 'PERSON_REPORT', 'ZONE_ACTIVITY', "
            "'OPERATION_SUMMARY', 'FORENSIC_TIMELINE')",
            name="check_report_type_valid",
        ),
        CheckConstraint(
            "classification IN ('RESTRICTED', 'CONFIDENTIAL', 'SECRET')",
            name="check_classification_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="check_report_status_valid",
        ),
        Index("idx_reports_generated_by", "generated_by"),
        Index("idx_reports_generated_at", "generated_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<Report(id={self.id}, report_type='{self.report_type}', "
            f"title='{self.title}', status='{self.status}')>"
        )


class ForensicJobType(str, PyEnum):
    """Forensic job type enumeration"""

    FACE_SEARCH = "FACE_SEARCH"
    OBJECT_SEARCH = "OBJECT_SEARCH"
    ZONE_SEARCH = "ZONE_SEARCH"
    TIMELINE_SEARCH = "TIMELINE_SEARCH"


class ForensicJobStatus(str, PyEnum):
    """Forensic job status enumeration"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ForensicJob(Base, UUIDMixin):
    """Forensic job model for async search tracking"""

    __tablename__ = "forensic_jobs"

    # Job type
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Job type (FACE_SEARCH, OBJECT_SEARCH, ZONE_SEARCH, TIMELINE_SEARCH)",
    )

    # Search parameters
    search_params: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Search parameters (query, filters, date range, etc.)"
    )

    # Job status
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
        index=True,
        comment="Job status (PENDING, RUNNING, COMPLETED, FAILED)",
    )

    # Results
    result_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of results found"
    )
    results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Array of detection event IDs or result objects"
    )

    # User tracking
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the job",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()", comment="Job creation timestamp"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Job completion timestamp"
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error message if job failed"
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship("User", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('FACE_SEARCH', 'OBJECT_SEARCH', 'ZONE_SEARCH', 'TIMELINE_SEARCH')",
            name="check_job_type_valid",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="check_forensic_job_status_valid",
        ),
        Index("idx_forensic_jobs_created_by", "created_by"),
        Index("idx_forensic_jobs_status", "status"),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<ForensicJob(id={self.id}, job_type='{self.job_type}', "
            f"status='{self.status}', result_count={self.result_count})>"
        )
