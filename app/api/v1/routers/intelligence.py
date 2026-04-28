"""
Intelligence Routers — Phase 18, 19, 20

Provides API endpoints for Forensic Search, Analytics, and Report Generation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, require_analyst, require_role
from app.core.database import get_session
from app.models.user import UserRole, User
from app.services.analytics_service import AnalyticsService
from app.services.forensic_service import ForensicService
from app.services.report_service import ReportService

router = APIRouter()


# ---------------------------------------------------------------------------
# FORENSICS (Phase 18)
# ---------------------------------------------------------------------------


@router.post("/forensics/face-search", tags=["Forensics"])
async def start_face_search(
    params: Dict[str, Any],
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Start async face similarity search.

    Requires ANALYST role or higher.

    Request Body:
    - **embedding**: Optional 512-dim face embedding vector
    - **watchlist_entry_id**: Optional watchlist entry UUID to search by
    - **similarity_threshold**: Minimum similarity (default 0.85)
    - **from_dt**: Start datetime filter (ISO format)
    - **to_dt**: End datetime filter (ISO format)
    - **feed_ids**: Optional list of feed UUIDs to scope search
    - **zone_ids**: Optional list of zone UUIDs to scope search

    Returns:
    - **job_id**: Async job ID to poll for results
    - **status**: Initial job status (PENDING)
    """
    service = ForensicService(db)
    job = await service.create_search_job(
        job_type="FACE_SEARCH",
        params=params,
        created_by=current_user.id,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.post("/forensics/object-search", tags=["Forensics"])
async def start_object_search(
    params: Dict[str, Any],
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Start async object class search.

    Requires ANALYST role or higher.

    Request Body:
    - **object_class**: Object class to search (e.g., 'weapon', 'vehicle')
    - **confidence_threshold**: Minimum confidence (default 0.75)
    - **from_dt**: Start datetime filter
    - **to_dt**: End datetime filter
    - **feed_ids**: Optional feed scope
    - **zone_ids**: Optional zone scope

    Returns:
    - **job_id**: Async job ID
    - **status**: Initial job status
    """
    service = ForensicService(db)
    job = await service.create_search_job(
        job_type="OBJECT_SEARCH",
        params=params,
        created_by=current_user.id,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.post("/forensics/zone-search", tags=["Forensics"])
async def start_zone_search(
    params: Dict[str, Any],
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Start async zone-based event search.

    Requires ANALYST role or higher.

    Request Body:
    - **zone_id**: Zone UUID to search
    - **event_type**: Optional detection type filter
    - **from_dt**: Start datetime filter
    - **to_dt**: End datetime filter

    Returns:
    - **job_id**: Async job ID
    - **status**: Initial job status
    """
    service = ForensicService(db)
    job = await service.create_search_job(
        job_type="ZONE_SEARCH",
        params=params,
        created_by=current_user.id,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.post("/forensics/timeline-search", tags=["Forensics"])
async def start_timeline_search(
    params: Dict[str, Any],
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Start async person movement timeline reconstruction.

    Requires ANALYST role or higher.

    Request Body:
    - **person_id**: TrackedPerson UUID
    - **from_dt**: Start datetime filter
    - **to_dt**: End datetime filter

    Returns:
    - **job_id**: Async job ID
    - **status**: Initial job status
    """
    service = ForensicService(db)
    job = await service.create_search_job(
        job_type="TIMELINE_SEARCH",
        params=params,
        created_by=current_user.id,
    )
    return {"job_id": str(job.id), "status": job.status}


@router.get("/forensics/jobs/{job_id}", tags=["Forensics"])
async def get_forensic_job(
    job_id: UUID,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get forensic job status and results.

    Requires ANALYST role or higher.

    Path Parameters:
    - **job_id**: Forensic job UUID

    Returns:
    - Job status, progress, and results when completed

    Errors:
    - 404: Job not found
    """
    service = ForensicService(db)
    job = await service.get_job_status(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forensic job {job_id} not found",
        )

    return {
        "job_id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "result_count": job.result_count,
        "results": job.results,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


# ---------------------------------------------------------------------------
# ANALYTICS (Phase 19)
# ---------------------------------------------------------------------------


@router.get("/analytics/summary", tags=["Analytics"])
async def get_analytics_summary(
    from_dt: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    to_dt: Optional[str] = Query(None, description="End datetime (ISO format)"),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get mission analytics summary.

    Requires ANALYST role or higher.

    Query Parameters:
    - **from_dt**: Start datetime (ISO format, default: 7 days ago)
    - **to_dt**: End datetime (ISO format, default: now)

    Returns:
    - Total alerts by priority, watchlist matches, zone breaches,
      persons tracked, false positive rate
    """
    service = AnalyticsService(db)

    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    return await service.get_summary(from_dt=from_datetime, to_dt=to_datetime)


@router.get("/analytics/alerts", tags=["Analytics"])
async def get_alerts_timeline(
    from_dt: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    to_dt: Optional[str] = Query(None, description="End datetime (ISO format)"),
    granularity: str = Query("hour", description="Time bucket granularity: 'hour' or 'day'"),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get alerts over time for line chart visualization.

    Requires ANALYST role or higher.

    Query Parameters:
    - **from_dt**: Start datetime
    - **to_dt**: End datetime
    - **granularity**: 'hour' or 'day' (default: 'hour')

    Returns:
    - List of time buckets with alert counts by priority
    """
    service = AnalyticsService(db)

    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    return await service.get_alerts_timeline(
        from_dt=from_datetime,
        to_dt=to_datetime,
        granularity=granularity,
    )


@router.get("/analytics/distribution", tags=["Analytics"])
async def get_alert_distribution(
    from_dt: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    to_dt: Optional[str] = Query(None, description="End datetime (ISO format)"),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get alert type distribution for donut chart.

    Requires ANALYST role or higher.

    Returns:
    - List of {alert_type, count, percentage} dicts
    """
    service = AnalyticsService(db)

    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    return await service.get_alert_distribution(from_dt=from_datetime, to_dt=to_datetime)


@router.get("/analytics/zones", tags=["Analytics"])
async def get_zone_heatmap(
    from_dt: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    to_dt: Optional[str] = Query(None, description="End datetime (ISO format)"),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get zone activity heatmap data (zones × hours of day).

    Requires ANALYST role or higher.

    Returns:
    - List of {zone_id, hour, alert_count} dicts
    """
    service = AnalyticsService(db)

    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    return await service.get_zone_heatmap(from_dt=from_datetime, to_dt=to_datetime)


@router.get("/analytics/performance", tags=["Analytics"])
async def get_ml_performance(
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get ML model performance metrics.

    Requires ANALYST role or higher.

    Returns:
    - Model accuracy, false positive rate trend, latency metrics
    """
    service = AnalyticsService(db)
    return await service.get_ml_performance()


@router.get("/analytics/top-feeds", tags=["Analytics"])
async def get_top_feeds(
    from_dt: Optional[str] = Query(None, description="Start datetime (ISO format)"),
    to_dt: Optional[str] = Query(None, description="End datetime (ISO format)"),
    limit: int = Query(10, ge=1, le=50, description="Number of top feeds to return"),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get most active feeds by alert count.

    Requires ANALYST role or higher.

    Returns:
    - List of {feed_id, alert_count} sorted descending
    """
    service = AnalyticsService(db)

    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    return await service.get_top_feeds(from_dt=from_datetime, to_dt=to_datetime, limit=limit)


# ---------------------------------------------------------------------------
# REPORTS (Phase 20)
# ---------------------------------------------------------------------------


@router.post("/reports", tags=["Reports"])
async def generate_report(
    title: str,
    report_type: str,
    classification: str = "RESTRICTED",
    summary: Optional[str] = None,
    analyst_notes: Optional[str] = None,
    detection_event_ids: Optional[List[str]] = None,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Generate an intelligence report as PDF.

    Requires ANALYST role or higher.

    Query Parameters:
    - **title**: Report title
    - **report_type**: INCIDENT_REPORT | PERSON_REPORT | ZONE_ACTIVITY | OPERATION_SUMMARY | FORENSIC_TIMELINE
    - **classification**: RESTRICTED | CONFIDENTIAL | SECRET (default: RESTRICTED)
    - **summary**: Optional executive summary text
    - **analyst_notes**: Optional analyst notes
    - **detection_event_ids**: Optional list of detection event IDs to include

    Returns:
    - Report metadata with job_id for async tracking
    """
    service = ReportService(db)

    data = {
        "summary": summary or f"Intelligence report: {title}",
        "analyst_notes": analyst_notes or "",
        "detection_events": [],
    }

    report = await service.generate_report(
        title=title,
        report_type=report_type,
        classification=classification,
        data=data,
        generated_by=current_user.id,
        detection_event_ids=detection_event_ids,
    )

    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": report.report_type,
        "classification": report.classification,
        "status": report.status,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "file_path": report.file_path,
    }


@router.get("/reports", tags=["Reports"])
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    List reports with optional filtering.

    Requires ANALYST role or higher.

    Returns:
    - List of report metadata
    """
    service = ReportService(db)
    reports = await service.list_reports(
        report_type=report_type,
        skip=skip,
        limit=limit,
    )

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "report_type": r.report_type,
            "classification": r.classification,
            "status": r.status,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}", tags=["Reports"])
async def get_report(
    report_id: UUID,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get report metadata and status.

    Requires ANALYST role or higher.

    Path Parameters:
    - **report_id**: Report UUID

    Returns:
    - Report metadata

    Errors:
    - 404: Report not found
    """
    service = ReportService(db)
    report = await service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": report.report_type,
        "classification": report.classification,
        "status": report.status,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "file_path": report.file_path,
        "detection_event_ids": report.detection_event_ids,
    }


@router.get("/reports/{report_id}/download", tags=["Reports"])
async def download_report(
    report_id: UUID,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_session),
):
    """
    Get presigned download URL for report PDF.

    Requires ANALYST role or higher.

    Path Parameters:
    - **report_id**: Report UUID

    Returns:
    - Presigned MinIO URL for PDF download

    Errors:
    - 404: Report not found
    - 503: Storage unavailable
    """
    service = ReportService(db)
    report = await service.get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    if report.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready for download (status: {report.status})",
        )

    url = await service.get_download_url(report_id)

    if url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable for download",
        )

    return {"download_url": url, "expires_in_seconds": 3600}
