"""
Watchlist Pydantic Schemas — Phase 10

Data models for watchlist entry creation, updates, and responses.
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.watchlist_entry import ThreatCategory, WatchlistStatus

class WatchlistEntryBase(BaseModel):
    """Base schema for watchlist entries"""
    name: Optional[str] = Field(None, max_length=255)
    alias: Optional[str] = Field(None, max_length=255)
    threat_category: ThreatCategory
    description: Optional[str] = None
    nationality: Optional[str] = Field(None, max_length=100)
    source_agency: Optional[str] = Field(None, max_length=100)

class WatchlistEntryCreate(WatchlistEntryBase):
    """Schema for creating a new watchlist entry"""
    # Images are usually handled via multipart form, so they aren't here
    pass

class WatchlistEntryUpdate(BaseModel):
    """Schema for updating a watchlist entry"""
    name: Optional[str] = Field(None, max_length=255)
    alias: Optional[str] = Field(None, max_length=255)
    threat_category: Optional[ThreatCategory] = None
    description: Optional[str] = None
    status: Optional[WatchlistStatus] = None

class WatchlistEntryResponse(WatchlistEntryBase):
    """Schema for watchlist entry responses"""
    id: UUID
    status: WatchlistStatus
    added_by: UUID
    approved_by: Optional[UUID] = None
    added_at: datetime
    approved_at: Optional[datetime] = None
    face_images: Optional[List[str]] = None
    
    model_config = {"from_attributes": True}

class WatchlistStatusUpdate(BaseModel):
    """Schema for updating status (e.g. approval)"""
    status: WatchlistStatus
    notes: Optional[str] = None
