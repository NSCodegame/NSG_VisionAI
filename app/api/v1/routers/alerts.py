"""
Alert Management API Router — Phase 13, Task 13.5

Provides REST endpoints for alert acknowledgement, resolution, and management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, require_operator
from app.api.v1.schemas.alert import (
    AlertListResponse,
    AlertResponse,
    AcknowledgeAlertRequest,
    ResolveAlertRequest,
    FalsePositiveRequest,
    AddNoteRequest,
    BulkAcknowledgeRequest,
)
from app.core.database import get_session
from app.models.alert import Alert, AlertPriority, AlertStatus, AlertType
from app.models.user import User
from app.repositories.alert import AlertRepository
from app.services.alert_service import AlertService
from app.services.clip_export_service import ClipExportService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="List alerts",
    description="List alerts with filtering and pagination (OPERATOR+)",
)
async def list_alerts(
    request: Request,
    priority: Optional[AlertPriority] = Query(None, description="Filter by priority"),
    status_filter: Optional[AlertStatus] = Query(None, alias="status", description="Filter by status"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    feed_id: Optional[str] = Query(None, description="Filter by feed UUID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone UUID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    List alerts with optional filtering and pagination.

    Requires OPERATOR role or higher.

    Query Parameters:
    - **priority**: Filter by priority (P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW)
    - **status**: Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)
    - **alert_type**: Filter by type (WATCHLIST_MATCH, ZONE_BREACH, WEAPON_DETECTED, etc.)
    - **feed_id**: Filter by feed UUID
    - **zone_id**: Filter by zone UUID
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records (default: 100, max: 1000)

    Returns:
    - List of alerts with pagination metadata
    """
    alert_repo = AlertRepository(session)
    
    # Build filters
    filters = []
    if priority is not None:
        filters.append(Alert.priority == priority.value)
    if status_filter is not None:
        filters.append(Alert.status == status_filter.value)
    if alert_type is not None:
        filters.append(Alert.alert_type == alert_type.value)
    if feed_id:
        try:
            feed_uuid = UUID(feed_id)
            filters.append(Alert.feed_id == feed_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feed_id format: {feed_id}",
            )
    if zone_id:
        try:
            zone_uuid = UUID(zone_id)
            filters.append(Alert.zone_id == zone_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid zone_id format: {zone_id}",
            )

    # Get alerts with filters
    alerts = await alert_repo.get_multi(
        skip=skip,
        limit=limit,
        filters=filters if filters else None,
        order_by=[Alert.priority.asc(), Alert.triggered_at.desc()],
    )

    # Count total alerts with same filters
    total = await alert_repo.count(filters=filters if filters else None)

    # Convert to response schema
    alert_responses = [
        AlertResponse(
            id=str(alert.id),
            detection_event_id=str(alert.detection_event_id),
            alert_type=alert.alert_type,
            priority=alert.priority,
            status=alert.status,
            feed_id=str(alert.feed_id) if alert.feed_id else None,
            zone_id=str(alert.zone_id) if alert.zone_id else None,
            confidence_score=float(alert.confidence_score) if alert.confidence_score else None,
            triggered_at=alert.triggered_at.isoformat(),
            acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
            acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
            resolution_notes=alert.resolution_notes,
            false_positive_reason=alert.false_positive_reason,
            occurrence_count=alert.occurrence_count,
        )
        for alert in alerts
    ]

    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get alert details",
    description="Get alert details by ID (OPERATOR+)",
)
async def get_alert(
    request: Request,
    alert_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get alert details by ID.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **alert_id**: Alert UUID

    Returns:
    - Alert details with detection frame, person info, timeline

    Errors:
    - 404: Alert not found
    """
    alert_repo = AlertRepository(session)
    alert = await alert_repo.get(alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    return AlertResponse(
        id=str(alert.id),
        detection_event_id=str(alert.detection_event_id),
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        feed_id=str(alert.feed_id) if alert.feed_id else None,
        zone_id=str(alert.zone_id) if alert.zone_id else None,
        confidence_score=float(alert.confidence_score) if alert.confidence_score else None,
        triggered_at=alert.triggered_at.isoformat(),
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        resolution_notes=alert.resolution_notes,
        false_positive_reason=alert.false_positive_reason,
        occurrence_count=alert.occurrence_count,
    )


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge alert",
    description="Acknowledge alert (OPERATOR+)",
)
async def acknowledge_alert(
    request: Request,
    alert_id: UUID,
    ack_data: AcknowledgeAlertRequest,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Acknowledge alert.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **alert_id**: Alert UUID

    Request Body:
    - **notes**: Optional acknowledgement notes

    Returns:
    - Updated alert details

    Errors:
    - 404: Alert not found
    """
    alert_repo = AlertRepository(session)
    alert = await alert_repo.acknowledge(alert_id, current_user.id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    # Add notes if provided
    if ack_data.notes:
        # TODO: Implement notes functionality
        pass

    await session.commit()

    return AlertResponse(
        id=str(alert.id),
        detection_event_id=str(alert.detection_event_id),
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        feed_id=str(alert.feed_id) if alert.feed_id else None,
        zone_id=str(alert.zone_id) if alert.zone_id else None,
        confidence_score=float(alert.confidence_score) if alert.confidence_score else None,
        triggered_at=alert.triggered_at.isoformat(),
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        resolution_notes=alert.resolution_notes,
        false_positive_reason=alert.false_positive_reason,
        occurrence_count=alert.occurrence_count,
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve alert",
    description="Resolve alert with notes (OPERATOR+)",
)
async def resolve_alert(
    request: Request,
    alert_id: UUID,
    resolve_data: ResolveAlertRequest,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Resolve alert with resolution notes.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **alert_id**: Alert UUID

    Request Body:
    - **resolution_notes**: Required resolution notes

    Returns:
    - Updated alert details

    Errors:
    - 404: Alert not found
    - 400: P1_CRITICAL alerts must be acknowledged first
    """
    alert_repo = AlertRepository(session)
    
    # Check if alert exists and is acknowledgeable for P1_CRITICAL
    alert = await alert_repo.get(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    # Prevent P1_CRITICAL auto-resolution without acknowledgement
    if alert.priority == AlertPriority.P1_CRITICAL.value and alert.status == AlertStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="P1_CRITICAL alerts must be acknowledged before resolution",
        )

    alert = await alert_repo.resolve(alert_id, resolve_data.resolution_notes)
    await session.commit()

    return AlertResponse(
        id=str(alert.id),
        detection_event_id=str(alert.detection_event_id),
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        feed_id=str(alert.feed_id) if alert.feed_id else None,
        zone_id=str(alert.zone_id) if alert.zone_id else None,
        confidence_score=float(alert.confidence_score) if alert.confidence_score else None,
        triggered_at=alert.triggered_at.isoformat(),
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        resolution_notes=alert.resolution_notes,
        false_positive_reason=alert.false_positive_reason,
        occurrence_count=alert.occurrence_count,
    )


@router.post(
    "/{alert_id}/false-positive",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark as false positive",
    description="Mark alert as false positive with reason (OPERATOR+)",
)
async def mark_false_positive(
    request: Request,
    alert_id: UUID,
    fp_data: FalsePositiveRequest,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Mark alert as false positive.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **alert_id**: Alert UUID

    Request Body:
    - **reason**: Required reason for false positive classification

    Returns:
    - Updated alert details

    Errors:
    - 404: Alert not found
    """
    alert_repo = AlertRepository(session)
    alert = await alert_repo.mark_false_positive(alert_id, fp_data.reason)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    await session.commit()

    return AlertResponse(
        id=str(alert.id),
        detection_event_id=str(alert.detection_event_id),
        alert_type=alert.alert_type,
        priority=alert.priority,
        status=alert.status,
        feed_id=str(alert.feed_id) if alert.feed_id else None,
        zone_id=str(alert.zone_id) if alert.zone_id else None,
        confidence_score=float(alert.confidence_score) if alert.confidence_score else None,
        triggered_at=alert.triggered_at.isoformat(),
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        resolution_notes=alert.resolution_notes,
        false_positive_reason=alert.false_positive_reason,
        occurrence_count=alert.occurrence_count,
    )


@router.post(
    "/bulk-acknowledge",
    status_code=status.HTTP_200_OK,
    summary="Bulk acknowledge alerts",
    description="Bulk acknowledge P4_LOW alerts (OPERATOR+)",
)
async def bulk_acknowledge_alerts(
    request: Request,
    bulk_data: BulkAcknowledgeRequest,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Bulk acknowledge multiple P4_LOW alerts.

    Requires OPERATOR role or higher.

    Request Body:
    - **alert_ids**: List of alert UUIDs (max 100)
    - **notes**: Optional bulk acknowledgement notes

    Returns:
    - Success count and failed alert IDs

    Note: Only P4_LOW alerts can be bulk acknowledged for safety.
    """
    if len(bulk_data.alert_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 alerts can be bulk acknowledged at once",
        )

    alert_repo = AlertRepository(session)
    success_count = 0
    failed_ids = []

    for alert_id_str in bulk_data.alert_ids:
        try:
            alert_id = UUID(alert_id_str)
            
            # Check if alert is P4_LOW
            alert = await alert_repo.get(alert_id)
            if alert is None:
                failed_ids.append(alert_id_str)
                continue
                
            if alert.priority != AlertPriority.P4_LOW.value:
                failed_ids.append(alert_id_str)
                continue

            # Acknowledge
            await alert_repo.acknowledge(alert_id, current_user.id)
            success_count += 1

        except (ValueError, Exception):
            failed_ids.append(alert_id_str)

    await session.commit()

    return {
        "success_count": success_count,
        "failed_alert_ids": failed_ids,
        "message": f"Successfully acknowledged {success_count} alerts",
    }


@router.get(
    "/{alert_id}/thumbnail",
    status_code=status.HTTP_200_OK,
    summary="Get alert thumbnail",
    description="Get detection frame thumbnail (OPERATOR+)",
)
async def get_alert_thumbnail(
    request: Request,
    alert_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get detection frame thumbnail for alert.

    Requires OPERATOR role or higher.
    """
    # TODO: Implement thumbnail retrieval from MinIO
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Thumbnail retrieval not yet implemented",
    )


@router.post(
    "/{alert_id}/export-clip",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export annotated video clip",
    description="Export 30-second annotated video clip around detection event (ANALYST+)",
)
async def export_alert_clip(
    request: Request,
    alert_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Export a 30-second annotated video clip around the alert's detection event.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **alert_id**: Alert UUID

    Returns:
    - download_url: Presigned MinIO URL (1-hour expiry)
    - clip_path: Storage path
    - expires_in_seconds: URL expiry

    Errors:
    - 404: Alert not found
    - 422: No archived segment available for this event
    """
    alert_repo = AlertRepository(session)
    alert = await alert_repo.get(alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    clip_service = ClipExportService(session)
    try:
        result = await clip_service.export_clip(
            detection_event_id=alert.detection_event_id,
            requested_by=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )