"""Main FastAPI application"""
import os
import warnings

# Suppress TensorFlow/oneDNN noise before any imports
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.middleware.audit_middleware import AuditLoggingMiddleware
from app.api.v1.routers import (
    auth,
    feeds,
    users,
    zones,
    watchlist,
    tracking,
    websocket,
    telemetry,
    health,
    intelligence,
    alerts,
    admin,
    streams,
    webcam,
)
from app.core.config import settings

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Defense-grade AI/ML surveillance system for India's National Security Guard",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add audit logging middleware
app.add_middleware(AuditLoggingMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(feeds.router, prefix="/api/v1")
app.include_router(zones.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(streams.router, prefix="/api/v1")
app.include_router(webcam.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    # Validate configuration
    try:
        settings.validate_on_startup()
        print(f"✓ {settings.app_name} v{settings.app_version} started successfully")
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Debug mode: {settings.debug}")
    except ValueError as e:
        print(f"✗ Configuration validation failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print(f"✓ {settings.app_name} shutdown complete")
