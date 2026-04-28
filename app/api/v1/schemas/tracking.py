"""
Tracking Pydantic Schemas — Phase 11

Data models for tracked persons, trajectories, and operator labels.
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.tracked_person import OperatorLabel

class TrajectoryPoint(BaseModel):
    """Schema for a single trajectory point"""
    feed_id: UUID
    timestamp: datetime
    position: dict = Field(..., description="Coordinates {x, y} as percentages (0.0-1.0)")

class TrackedPersonBase(BaseModel):
    """Base schema for tracked persons"""
    track_id: str
    operator_label: Optional[OperatorLabel] = OperatorLabel.UNKNOWN
    notes: Optional[str] = None
    watchlist_match: bool = False
    watchlist_entry_id: Optional[UUID] = None

class TrackedPersonResponse(TrackedPersonBase):
    """Schema for tracked person responses"""
    id: UUID
    first_seen_at: datetime
    last_seen_at: datetime
    feed_ids_seen: Optional[dict] = None
    trajectory: Optional[dict] = None
    
    model_config = {"from_attributes": True}

class OperatorLabelUpdate(BaseModel):
    """Schema for updating operator labels"""
    label: OperatorLabel
    notes: Optional[str] = None
