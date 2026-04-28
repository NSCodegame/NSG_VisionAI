"""
Telemetry Router — Phase 22, Task 22.1

Handles real-time GPS and health telemetry updates from aerial sensors (Drones).
Supports MAVLink-compatible JSON payloads over HTTP/HTTPS.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, require_commander
from app.core.database import get_db
from app.services.telemetry_service import TelemetryService

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str = "OK"

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

class DroneTelemetryIn(BaseModel):
    """MAVLink-structured telemetry input"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float = Field(..., description="Altitude in meters (AMSL)")
    heading: float = Field(0.0, ge=0, le=360, description="Yaw heading in degrees")
    battery_percentage: Optional[int] = Field(None, ge=0, le=100)
    velocity_ms: Optional[float] = Field(None, description="Velocity in m/s")
    status_text: Optional[str] = Field(None, description="Latest MAVLink status message")

@router.post(
    "/{feed_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_commander)]
)
async def update_drone_telemetry(
    feed_id: UUID,
    telemetry: DroneTelemetryIn,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Push new telemetry data for a drone feed.
    Updates feed location and triggers spatial alerts if necessary.
    """
    service = TelemetryService(db)
    success = await service.update_drone_location(
        feed_id=feed_id,
        lat=telemetry.latitude,
        lon=telemetry.longitude,
        alt=telemetry.altitude,
        metadata={
            "battery": telemetry.battery_percentage,
            "status": telemetry.status_text,
            "heading": telemetry.heading
        }
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UAV feed not found or access denied"
        )
        
    return SuccessResponse(message="Telemetry accepted")
