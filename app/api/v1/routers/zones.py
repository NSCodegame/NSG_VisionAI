"""Security Zone management endpoints"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_admin, require_commander, require_operator
from app.api.v1.schemas.zone import (
    CreateZoneRequest,
    UpdateThreatLevelRequest,
    UpdateThreatLevelResponse,
    UpdateZoneRequest,
    ZoneListResponse,
    ZoneResponse,
)
from app.core.database import get_session
from app.models.security_zone import ThreatLevel, ZoneType
from app.models.user import User
from app.repositories.security_zone import SecurityZoneRepository
from app.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["Security Zones"])


def _extract_ip_address(request: Request) -> Optional[str]:
    """Extract IP address from request"""
    return request.client.host if request.client else None


@router.get(
    "",
    response_model=ZoneListResponse,
    status_code=status.HTTP_200_OK,
    summary="List security zones",
    description="List all security zones with optional filtering (OPERATOR+)",
)
async def list_zones(
    request: Request,
    zone_type: Optional[ZoneType] = Query(None, description="Filter by zone type"),
    threat_level: Optional[ThreatLevel] = Query(None, description="Filter by threat level"),
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    List all security zones with optional filtering.

    Requires OPERATOR role or higher.

    Query Parameters:
    - **zone_type**: Filter by zone type (PERIMETER, RESTRICTED, PUBLIC, INNER_CORDON)
    - **threat_level**: Filter by threat level (GREEN, AMBER, RED, CRITICAL)

    Returns:
    - List of zones with polygon coordinates
    - No pagination (zones are limited in number)
    """
    zone_service = ZoneService(session)

    # Get zones with filters
    zones = await zone_service.get_zones(
        zone_type=zone_type,
        threat_level=threat_level,
    )

    # Convert to response schema
    zone_responses = [
        ZoneResponse(
            id=str(zone.id),
            name=zone.name,
            zone_type=zone.zone_type,
            polygon_coordinates=zone.polygon_coordinates,
            threat_level=zone.threat_level,
            created_at=zone.created_at.isoformat(),
            updated_at=zone.updated_at.isoformat(),
        )
        for zone in zones
    ]

    return ZoneListResponse(
        zones=zone_responses,
        total=len(zone_responses),
    )


@router.post(
    "",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create security zone",
    description="Create new security zone with polygon coordinates (ADMIN only)",
)
async def create_zone(
    request: Request,
    zone_data: CreateZoneRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Create new security zone.

    Requires ADMIN role.

    Request Body:
    - **name**: Zone name
    - **zone_type**: Zone type (PERIMETER, RESTRICTED, PUBLIC, INNER_CORDON)
    - **polygon_coordinates**: GeoJSON polygon with at least 3 points
    - **threat_level**: Initial threat level (default: GREEN)

    Polygon Format:
    ```json
    {
        "type": "Polygon",
        "coordinates": [
            [
                {"lat": 28.6139, "lng": 77.2090},
                {"lat": 28.6140, "lng": 77.2091},
                {"lat": 28.6141, "lng": 77.2089},
                {"lat": 28.6139, "lng": 77.2090}
            ]
        ]
    }
    ```

    Returns:
    - Created zone details

    Errors:
    - 400: Invalid polygon coordinates
    """
    zone_service = ZoneService(session)
    ip_address = _extract_ip_address(request)

    try:
        zone = await zone_service.create_zone(
            name=zone_data.name,
            zone_type=zone_data.zone_type,
            polygon_coordinates=zone_data.polygon_coordinates,
            threat_level=zone_data.threat_level,
            created_by=current_user.id,
            ip_address=ip_address,
        )

        return ZoneResponse(
            id=str(zone.id),
            name=zone.name,
            zone_type=zone.zone_type,
            polygon_coordinates=zone.polygon_coordinates,
            threat_level=zone.threat_level,
            created_at=zone.created_at.isoformat(),
            updated_at=zone.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Get zone details",
    description="Get security zone details by ID (OPERATOR+)",
)
async def get_zone(
    request: Request,
    zone_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get security zone details by ID.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **zone_id**: Zone UUID

    Returns:
    - Zone details with polygon coordinates

    Errors:
    - 404: Zone not found
    """
    zone_repo = SecurityZoneRepository(session)
    zone = await zone_repo.get(zone_id)

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    return ZoneResponse(
        id=str(zone.id),
        name=zone.name,
        zone_type=zone.zone_type,
        polygon_coordinates=zone.polygon_coordinates,
        threat_level=zone.threat_level,
        created_at=zone.created_at.isoformat(),
        updated_at=zone.updated_at.isoformat(),
    )


@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Update zone",
    description="Update security zone details (ADMIN only)",
)
async def update_zone(
    request: Request,
    zone_id: UUID,
    zone_data: UpdateZoneRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Update security zone details.

    Requires ADMIN role.

    Path Parameters:
    - **zone_id**: Zone UUID

    Request Body (all fields optional for partial updates):
    - **name**: Zone name
    - **zone_type**: Zone type
    - **polygon_coordinates**: GeoJSON polygon coordinates

    Returns:
    - Updated zone details

    Errors:
    - 404: Zone not found
    - 400: Invalid polygon coordinates
    """
    zone_repo = SecurityZoneRepository(session)
    ip_address = _extract_ip_address(request)

    # Check if zone exists
    zone = await zone_repo.get(zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    zone_service = ZoneService(session)

    try:
        zone = await zone_service.update_zone(
            zone_id=zone_id,
            name=zone_data.name,
            zone_type=zone_data.zone_type,
            polygon_coordinates=zone_data.polygon_coordinates,
            updated_by=current_user.id,
            ip_address=ip_address,
        )

        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found",
            )

        return ZoneResponse(
            id=str(zone.id),
            name=zone.name,
            zone_type=zone.zone_type,
            polygon_coordinates=zone.polygon_coordinates,
            threat_level=zone.threat_level,
            created_at=zone.created_at.isoformat(),
            updated_at=zone.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put(
    "/{zone_id}/threat-level",
    response_model=UpdateThreatLevelResponse,
    status_code=status.HTTP_200_OK,
    summary="Update threat level",
    description="Update zone threat level and recalculate alert priorities (COMMANDER+)",
)
async def update_threat_level(
    request: Request,
    zone_id: UUID,
    threat_data: UpdateThreatLevelRequest,
    current_user: User = Depends(require_commander),
    session: AsyncSession = Depends(get_session),
):
    """
    Update zone threat level and recalculate alert priorities.

    Requires COMMANDER role or higher.

    Path Parameters:
    - **zone_id**: Zone UUID

    Request Body:
    - **threat_level**: New threat level (GREEN, AMBER, RED, CRITICAL)
    - **confirmation**: Required for CRITICAL level (default: false)

    Returns:
    - Updated zone details
    - Number of alerts with recalculated priorities

    Errors:
    - 404: Zone not found
    - 400: CRITICAL level requires confirmation
    """
    zone_repo = SecurityZoneRepository(session)
    ip_address = _extract_ip_address(request)

    # Check if zone exists
    zone = await zone_repo.get(zone_id)
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_id} not found",
        )

    zone_service = ZoneService(session)

    try:
        zone, affected_count = await zone_service.update_threat_level(
            zone_id=zone_id,
            threat_level=threat_data.threat_level,
            confirmation=threat_data.confirmation,
            updated_by=current_user.id,
            ip_address=ip_address,
        )

        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found",
            )

        return UpdateThreatLevelResponse(
            zone=ZoneResponse(
                id=str(zone.id),
                name=zone.name,
                zone_type=zone.zone_type,
                polygon_coordinates=zone.polygon_coordinates,
                threat_level=zone.threat_level,
                created_at=zone.created_at.isoformat(),
                updated_at=zone.updated_at.isoformat(),
            ),
            affected_alerts=affected_count,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete zone",
    description="Delete security zone (checks for dependencies) (ADMIN only)",
)
async def delete_zone(
    request: Request,
    zone_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete security zone.

    Requires ADMIN role.

    Path Parameters:
    - **zone_id**: Zone UUID

    Returns:
    - 204 No Content on success

    Errors:
    - 404: Zone not found
    - 400: Zone has active feeds (cannot delete)
    """
    zone_service = ZoneService(session)
    ip_address = _extract_ip_address(request)

    try:
        zone = await zone_service.delete_zone(
            zone_id=zone_id,
            deleted_by=current_user.id,
            ip_address=ip_address,
        )

        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone {zone_id} not found",
            )

        return None

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
