"""Security Zone Pydantic schemas"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.security_zone import ThreatLevel, ZoneType


class CreateZoneRequest(BaseModel):
    """Request schema for creating a security zone"""

    name: str = Field(..., min_length=1, max_length=255, description="Zone name")
    zone_type: ZoneType = Field(..., description="Zone type")
    polygon_coordinates: Dict[str, Any] = Field(
        ..., description="GeoJSON polygon coordinates"
    )
    threat_level: ThreatLevel = Field(
        default=ThreatLevel.GREEN, description="Initial threat level"
    )

    @field_validator("polygon_coordinates")
    @classmethod
    def validate_polygon_structure(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic polygon structure"""
        if not isinstance(v, dict):
            raise ValueError("polygon_coordinates must be a dictionary")
        if v.get("type") != "Polygon":
            raise ValueError("polygon_coordinates type must be 'Polygon'")
        if "coordinates" not in v:
            raise ValueError("polygon_coordinates must have 'coordinates' field")
        return v


class UpdateZoneRequest(BaseModel):
    """Request schema for updating a security zone"""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Zone name")
    zone_type: Optional[ZoneType] = Field(None, description="Zone type")
    polygon_coordinates: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON polygon coordinates"
    )

    @field_validator("polygon_coordinates")
    @classmethod
    def validate_polygon_structure(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate basic polygon structure"""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("polygon_coordinates must be a dictionary")
        if v.get("type") != "Polygon":
            raise ValueError("polygon_coordinates type must be 'Polygon'")
        if "coordinates" not in v:
            raise ValueError("polygon_coordinates must have 'coordinates' field")
        return v


class UpdateThreatLevelRequest(BaseModel):
    """Request schema for updating zone threat level"""

    threat_level: ThreatLevel = Field(..., description="New threat level")
    confirmation: bool = Field(
        default=False,
        description="Confirmation required for CRITICAL level",
    )


class ZoneResponse(BaseModel):
    """Response schema for security zone"""

    id: str = Field(..., description="Zone UUID")
    name: str = Field(..., description="Zone name")
    zone_type: str = Field(..., description="Zone type")
    polygon_coordinates: Dict[str, Any] = Field(..., description="GeoJSON polygon coordinates")
    threat_level: str = Field(..., description="Current threat level")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")

    class Config:
        from_attributes = True


class ZoneListResponse(BaseModel):
    """Response schema for zone list"""

    zones: List[ZoneResponse] = Field(..., description="List of zones")
    total: int = Field(..., description="Total number of zones")


class UpdateThreatLevelResponse(BaseModel):
    """Response schema for threat level update"""

    zone: ZoneResponse = Field(..., description="Updated zone")
    affected_alerts: int = Field(
        ..., description="Number of alerts with recalculated priorities"
    )
