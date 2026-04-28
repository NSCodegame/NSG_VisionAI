"""
Tracking API Router — Phase 11, Task 11.3

Provides REST endpoints for querying tracked individuals and trajectories.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.schemas.tracking import (
    OperatorLabelUpdate,
    TrackedPersonResponse,
)
from app.core.database import get_session
from app.services.tracked_person_service import TrackedPersonService

router = APIRouter(prefix="/tracking", tags=["Tracking"])

@router.get("/persons", response_model=List[TrackedPersonResponse])
async def list_tracked_persons(
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """List all recently tracked individuals across all feeds."""
    service = TrackedPersonService(db)
    return await service.list_active_persons(limit=limit)

@router.get("/persons/{person_id}", response_model=TrackedPersonResponse)
async def get_tracked_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get detailed history and trajectory for a specific individual."""
    service = TrackedPersonService(db)
    person = await service.person_repo.get(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Tracked person not found")
    return person

@router.patch("/persons/{person_id}/label", response_model=TrackedPersonResponse)
async def update_person_label(
    person_id: UUID,
    update: OperatorLabelUpdate,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Manually assign an operator label (e.g., SUSPECT) to an individual.
    """
    service = TrackedPersonService(db)
    person = await service.update_operator_label(person_id, update.label, update.notes)
    if not person:
        raise HTTPException(status_code=404, detail="Tracked person not found")
    return person

@router.get("/watchlist-matches", response_model=List[TrackedPersonResponse])
async def list_watchlist_matches(
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """List only tracked persons that triggered a watchlist match."""
    service = TrackedPersonService(db)
    return await service.person_repo.get_by_watchlist_match()
