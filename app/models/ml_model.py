"""ML Model Management Model"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ModelType(str, PyEnum):
    """ML model type enumeration"""

    DETECTION = "DETECTION"  # YOLOv8 object detection
    TRACKING = "TRACKING"  # ByteTrack person tracking
    FACE_RECOGNITION = "FACE_RECOGNITION"  # RetinaFace + ArcFace
    ANOMALY = "ANOMALY"  # LSTM anomaly detection


class ModelFramework(str, PyEnum):
    """ML framework enumeration"""

    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORRT = "tensorrt"


class MLModel(Base, UUIDMixin):
    """ML model management for version tracking and deployment"""

    __tablename__ = "ml_models"

    # Model identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Model name")
    version: Mapped[str] = mapped_column(String(50), nullable=False, comment="Model version (e.g., v1.0.0)")

    # Model classification
    model_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Model type (DETECTION, TRACKING, FACE_RECOGNITION, ANOMALY)",
    )
    framework: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Framework (pytorch, onnx, tensorrt)"
    )

    # Model files
    weights_path: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Path to model weights file"
    )
    config_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Path to model configuration file"
    )

    # Performance metrics
    accuracy_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Accuracy metrics: {mAP, precision, recall, per_class_metrics}",
    )

    # Deployment status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Whether model is currently active"
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Deployment timestamp"
    )
    deployed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who deployed this model",
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()", comment="Model creation timestamp"
    )

    # Relationships
    deployed_by_user: Mapped["User"] = relationship("User", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "model_type IN ('DETECTION', 'TRACKING', 'FACE_RECOGNITION', 'ANOMALY')",
            name="check_model_type_valid",
        ),
        CheckConstraint(
            "framework IN ('pytorch', 'onnx', 'tensorrt')",
            name="check_framework_valid",
        ),
        Index("idx_ml_models_type", "model_type"),
        Index("idx_ml_models_active", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<MLModel(id={self.id}, name='{self.name}', version='{self.version}', "
            f"model_type='{self.model_type}', is_active={self.is_active})>"
        )
