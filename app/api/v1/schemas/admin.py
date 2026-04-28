"""
Admin API Schemas — Phase 21, Task 21.3

Pydantic schemas for administrative endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ML Model Management Schemas
class MLModelResponse(BaseModel):
    """ML model response schema"""
    id: str
    name: str
    version: str
    model_type: str
    framework: str
    weights_path: str
    config_path: Optional[str] = None
    accuracy_metrics: Optional[Dict[str, Any]] = None
    is_active: bool
    deployed_at: Optional[str] = None
    deployed_by: Optional[str] = None
    created_at: str


class MLModelListResponse(BaseModel):
    """ML model list response with pagination"""
    models: List[MLModelResponse]
    total: int
    skip: int
    limit: int


class UploadModelRequest(BaseModel):
    """Request schema for uploading ML models"""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Model type (DETECTION, TRACKING, FACE_RECOGNITION, ANOMALY)")
    framework: str = Field(..., description="Framework (pytorch, onnx, tensorrt)")


class DeployModelRequest(BaseModel):
    """Request schema for deploying ML models"""
    confirmed: bool = Field(..., description="Deployment confirmation (must be true)")


# System Health Schemas
class GPUMetrics(BaseModel):
    """GPU metrics schema"""
    device_id: int
    name: str
    utilization_percent: float
    memory_used_mb: int
    memory_total_mb: int
    temperature_c: Optional[float] = None


class SystemHealthResponse(BaseModel):
    """System health response schema"""
    status: str
    timestamp: str
    gpu_metrics: List[GPUMetrics]
    cpu_usage_percent: float
    ram_usage_percent: float
    active_streams: int
    max_streams: int
    redis_queue_depth: Dict[str, int]
    minio_storage_used_gb: float
    minio_storage_total_gb: float
    postgresql_connections_active: int
    postgresql_connections_max: int
    alert_processing_latency_ms: Dict[str, float]  # p50, p95, p99


class WorkerHealthResponse(BaseModel):
    """Worker health response schema"""
    worker_id: str
    worker_type: str
    status: str  # active, idle, offline
    current_task: Optional[str] = None
    last_heartbeat: Optional[str] = None
    processed_tasks: int
    failed_tasks: int
    uptime_seconds: int


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    """Audit log response schema"""
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str


class AuditLogListResponse(BaseModel):
    """Audit log list response with pagination"""
    logs: List[AuditLogResponse]
    total: int
    skip: int
    limit: int