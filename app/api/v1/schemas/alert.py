"""
Alert API Schemas — Phase 13, Task 13.5

Pydantic schemas for alert management endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Alert response schema"""
    id: str
    detection_event_id: str
    alert_type: str
    priority: str
    status: str
    feed_id: Optional[str] = None
    zone_id: Optional[str] = None
    confidence_score: Optional[float] = None
    triggered_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    false_positive_reason: Optional[str] = None
    occurrence_count: int


class AlertListResponse(BaseModel):
    """Alert list response with pagination"""
    alerts: List[AlertResponse]
    total: int
    skip: int
    limit: int


class AcknowledgeAlertRequest(BaseModel):
    """Request schema for acknowledging alerts"""
    notes: Optional[str] = Field(None, description="Optional acknowledgement notes")


class ResolveAlertRequest(BaseModel):
    """Request schema for resolving alerts"""
    resolution_notes: str = Field(..., description="Required resolution notes", min_length=1)


class FalsePositiveRequest(BaseModel):
    """Request schema for marking alerts as false positive"""
    reason: str = Field(..., description="Required reason for false positive", min_length=1)


class AddNoteRequest(BaseModel):
    """Request schema for adding notes to alerts"""
    note: str = Field(..., description="Note text", min_length=1)


class BulkAcknowledgeRequest(BaseModel):
    """Request schema for bulk acknowledging alerts"""
    alert_ids: List[str] = Field(..., description="List of alert UUIDs", max_items=100)
    notes: Optional[str] = Field(None, description="Optional bulk acknowledgement notes")