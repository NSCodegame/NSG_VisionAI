"""
Watchlist API Router — Phase 10, Task 10.3

Provides REST endpoints for biometric enrollment and monitoring.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, require_commander, require_admin
from app.api.v1.schemas.watchlist import (
    WatchlistEntryCreate,
    WatchlistEntryResponse,
    WatchlistEntryUpdate,
)
from app.core.database import get_session
from app.models.user import UserRole
from app.models.watchlist_entry import ThreatCategory
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.get("/", response_model=List[WatchlistEntryResponse])
async def list_watchlist(
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """List all watchlist entries."""
    service = WatchlistService(db)
    return await service.watchlist_repo.get_multi(limit=100)

@router.post("/", response_model=WatchlistEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist_entry(
    name: Optional[str] = Form(None),
    alias: Optional[str] = Form(None),
    threat_category: ThreatCategory = Form(...),
    description: Optional[str] = Form(None),
    nationality: Optional[str] = Form(None),
    source_agency: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Enroll a new person into the watchlist.
    Requires at least one clear facial image.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required for enrollment.")
    
    # Read image bytes
    image_bytes_list = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        image_bytes_list.append(await file.read())
        
    if not image_bytes_list:
        raise HTTPException(status_code=400, detail="No valid images provided.")

    service = WatchlistService(db)
    entry_data = {
        "name": name,
        "alias": alias,
        "threat_category": threat_category,
        "description": description,
        "nationality": nationality,
        "source_agency": source_agency
    }
    
    try:
        return await service.create_watchlist_entry(current_user.id, entry_data, image_bytes_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{entry_id}", response_model=WatchlistEntryResponse)
async def get_watchlist_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get detailed information about a watchlist entry."""
    service = WatchlistService(db)
    entry = await service.watchlist_repo.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return entry

@router.post("/{entry_id}/approve", response_model=WatchlistEntryResponse)
async def approve_watchlist_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_commander)
):
    """
    Approve a watchlist entry.
    Requires COMMANDER or ADMIN role.
    """
    service = WatchlistService(db)
    entry = await service.approve_entry(entry_id, current_user.id)
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return entry

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_admin)
):
    """Deactivate a watchlist entry (soft delete)."""
    service = WatchlistService(db)
    success = await service.watchlist_repo.deactivate(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return None
