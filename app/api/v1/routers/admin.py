"""
Admin API Router — Phase 21, Task 21.3

Provides administrative endpoints for ML model management, system health, and audit logs.
"""

import io
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_admin
from app.api.v1.schemas.admin import (
    AuditLogListResponse,
    AuditLogResponse,
    DeployModelRequest,
    MLModelListResponse,
    MLModelResponse,
)
from app.core.database import get_session
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.services.health_service import HealthService
from app.services.model_service import ModelService

router = APIRouter(prefix="/admin", tags=["Administration"])


# ---------------------------------------------------------------------------
# ML Model Management
# ---------------------------------------------------------------------------


@router.get(
    "/models",
    response_model=MLModelListResponse,
    status_code=status.HTTP_200_OK,
    summary="List ML models",
    description="List all ML models with metadata (ADMIN only)",
)
async def list_models(
    request: Request,
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all ML models. Requires ADMIN role."""
    model_service = ModelService(session)
    models = await model_service.get_models(model_type=model_type, skip=skip, limit=limit)

    model_responses = [
        MLModelResponse(
            id=str(m.id),
            name=m.name,
            version=m.version,
            model_type=m.model_type,
            framework=m.framework,
            weights_path=m.weights_path,
            config_path=m.config_path,
            accuracy_metrics=m.accuracy_metrics,
            is_active=m.is_active,
            deployed_at=m.deployed_at.isoformat() if m.deployed_at else None,
            deployed_by=str(m.deployed_by) if m.deployed_by else None,
            created_at=m.created_at.isoformat(),
        )
        for m in models
    ]

    return MLModelListResponse(
        models=model_responses,
        total=len(model_responses),
        skip=skip,
        limit=limit,
    )


@router.post(
    "/models",
    response_model=MLModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload ML model",
    description="Register a new ML model (ADMIN only)",
)
async def upload_model(
    request: Request,
    name: str,
    version: str,
    model_type: str,
    framework: str,
    weights_file: UploadFile = File(...),
    config_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Upload new ML model weights and configuration. Requires ADMIN role."""
    model_service = ModelService(session)

    try:
        # Upload weights to MinIO
        weights_content = await weights_file.read()
        weights_path = f"models/{model_type}/{name}/{version}/weights/{weights_file.filename}"

        config_path = None
        if config_file:
            config_content = await config_file.read()
            config_path = f"models/{model_type}/{name}/{version}/config/{config_file.filename}"
            # Upload config to MinIO (best-effort)
            try:
                from app.utils.minio_client import get_minio_client
                from app.core.config import settings

                client = get_minio_client()
                bucket = getattr(settings, "minio_models_bucket", "nsg-models")
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                client.put_object(
                    bucket_name=bucket,
                    object_name=config_path,
                    data=io.BytesIO(config_content),
                    length=len(config_content),
                )
            except Exception:
                pass  # Non-fatal

        # Upload weights to MinIO (best-effort)
        try:
            from app.utils.minio_client import get_minio_client
            from app.core.config import settings

            client = get_minio_client()
            bucket = getattr(settings, "minio_models_bucket", "nsg-models")
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.put_object(
                bucket_name=bucket,
                object_name=weights_path,
                data=io.BytesIO(weights_content),
                length=len(weights_content),
            )
        except Exception:
            pass  # Non-fatal

        model = await model_service.register_model(
            name=name,
            version=version,
            model_type=model_type,
            framework=framework,
            weights_path=weights_path,
            config_path=config_path,
            uploaded_by=current_user.id,
        )

        return MLModelResponse(
            id=str(model.id),
            name=model.name,
            version=model.version,
            model_type=model.model_type,
            framework=model.framework,
            weights_path=model.weights_path,
            config_path=model.config_path,
            accuracy_metrics=model.accuracy_metrics,
            is_active=model.is_active,
            deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
            deployed_by=str(model.deployed_by) if model.deployed_by else None,
            created_at=model.created_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/models/{model_id}/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate ML model",
    description="Run inference test on model (ADMIN only)",
)
async def validate_model(
    request: Request,
    model_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Validate model by running sample inference. Requires ADMIN role."""
    model_service = ModelService(session)
    try:
        result = await model_service.validate_model(model_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/models/{model_id}/deploy",
    response_model=MLModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Deploy ML model",
    description="Deploy ML model to production (ADMIN only)",
)
async def deploy_model(
    request: Request,
    model_id: UUID,
    deploy_data: DeployModelRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Deploy ML model to production. Requires ADMIN role and confirmation."""
    if not deploy_data.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment confirmation required (set confirmed=true)",
        )

    model_service = ModelService(session)
    try:
        model = await model_service.deploy_model(model_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return MLModelResponse(
        id=str(model.id),
        name=model.name,
        version=model.version,
        model_type=model.model_type,
        framework=model.framework,
        weights_path=model.weights_path,
        config_path=model.config_path,
        accuracy_metrics=model.accuracy_metrics,
        is_active=model.is_active,
        deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
        deployed_by=str(model.deployed_by) if model.deployed_by else None,
        created_at=model.created_at.isoformat(),
    )


@router.post(
    "/models/{model_id}/rollback",
    response_model=MLModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Rollback ML model",
    description="Rollback to previous model version (ADMIN only)",
)
async def rollback_model(
    request: Request,
    model_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Rollback to previous model version. Requires ADMIN role."""
    model_service = ModelService(session)

    # Get the model to find its type
    model = await model_service.get_model(model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    try:
        rolled_back = await model_service.rollback_model(model.model_type, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if rolled_back is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No previous model version available for rollback",
        )

    return MLModelResponse(
        id=str(rolled_back.id),
        name=rolled_back.name,
        version=rolled_back.version,
        model_type=rolled_back.model_type,
        framework=rolled_back.framework,
        weights_path=rolled_back.weights_path,
        config_path=rolled_back.config_path,
        accuracy_metrics=rolled_back.accuracy_metrics,
        is_active=rolled_back.is_active,
        deployed_at=rolled_back.deployed_at.isoformat() if rolled_back.deployed_at else None,
        deployed_by=str(rolled_back.deployed_by) if rolled_back.deployed_by else None,
        created_at=rolled_back.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# System Health Monitoring
# ---------------------------------------------------------------------------


@router.get(
    "/health/system",
    status_code=status.HTTP_200_OK,
    summary="Get system health",
    description="Get comprehensive system health metrics (ADMIN only)",
)
async def get_system_health(
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get comprehensive system health metrics. Requires ADMIN role."""
    health_service = HealthService(session)
    return await health_service.get_system_health()


@router.get(
    "/health/workers",
    status_code=status.HTTP_200_OK,
    summary="Get worker health",
    description="Get Celery worker health status (ADMIN only)",
)
async def get_worker_health(
    request: Request,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get Celery worker health status. Requires ADMIN role."""
    health_service = HealthService(session)
    return await health_service.get_worker_health()


@router.post(
    "/workers/{worker_id}/restart",
    status_code=status.HTTP_200_OK,
    summary="Restart worker",
    description="Restart specific Celery worker (ADMIN only)",
)
async def restart_worker(
    request: Request,
    worker_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Restart specific Celery worker. Requires ADMIN role."""
    health_service = HealthService(session)
    success = await health_service.restart_worker(worker_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found or could not be restarted",
        )

    return {"message": f"Worker {worker_id} restart initiated", "worker_id": worker_id}


# ---------------------------------------------------------------------------
# Audit Log Management
# ---------------------------------------------------------------------------


@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audit logs",
    description="List audit logs with filtering (ADMIN only)",
)
async def list_audit_logs(
    request: Request,
    user_id: Optional[str] = Query(None, description="Filter by user UUID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List audit logs with filtering. Requires ADMIN role."""
    from app.models.audit_log import AuditLog

    audit_repo = AuditLogRepository(session)

    filters = []
    if user_id:
        try:
            user_uuid = UUID(user_id)
            filters.append(AuditLog.user_id == user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_id format: {user_id}",
            )
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    logs = await audit_repo.get_multi(
        skip=skip,
        limit=limit,
        filters=filters if filters else None,
        order_by=[AuditLog.timestamp.desc()],
    )
    total = await audit_repo.count(filters=filters if filters else None)

    log_responses = [
        AuditLogResponse(
            id=str(log.id),
            user_id=str(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id) if log.resource_id else None,
            ip_address=str(log.ip_address) if log.ip_address else None,
            user_agent=log.user_agent,
            session_id=str(log.session_id) if log.session_id else None,
            details=log.details,
            timestamp=log.timestamp.isoformat(),
        )
        for log in logs
    ]

    return AuditLogListResponse(
        logs=log_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/audit/export",
    status_code=status.HTTP_200_OK,
    summary="Export audit logs to CSV",
    description="Export filtered audit logs as CSV (ADMIN only)",
)
async def export_audit_logs(
    request: Request,
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Export audit logs to CSV. Requires ADMIN role."""
    from app.models.audit_log import AuditLog

    audit_repo = AuditLogRepository(session)

    filters = []
    if user_id:
        try:
            filters.append(AuditLog.user_id == UUID(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_id: {user_id}",
            )
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    csv_content = await audit_repo.export_to_csv(
        filters=filters if filters else None
    )

    # Log the export itself
    await audit_repo.create(
        user_id=current_user.id,
        action="AUDIT_LOG_EXPORT",
        resource_type="AUDIT_LOG",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"filters": {"user_id": user_id, "action": action, "resource_type": resource_type}},
    )
    await session.commit()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
