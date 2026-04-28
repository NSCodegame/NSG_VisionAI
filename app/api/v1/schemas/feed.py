"""Video Feed schemas"""
from typing import Optional

from pydantic import BaseModel, Field

from app.models.video_feed import FeedStatus, FeedType


class CreateFeedRequest(BaseModel):
    """Create feed request schema"""

    name: str = Field(..., description="Feed name/identifier", min_length=1, max_length=255)
    feed_type: FeedType = Field(..., description="Feed type")
    rtsp_url: str = Field(..., description="RTSP URL (will be encrypted)", min_length=10)
    zone_id: Optional[str] = Field(None, description="Security zone UUID")
    location_name: Optional[str] = Field(None, description="Human-readable location name", max_length=255)
    latitude: Optional[float] = Field(None, description="GPS latitude coordinate", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="GPS longitude coordinate", ge=-180, le=180)
    ai_enabled: bool = Field(True, description="Enable AI processing for this feed")


class UpdateFeedRequest(BaseModel):
    """Update feed request schema (all fields optional for partial updates)"""

    name: Optional[str] = Field(None, description="Feed name/identifier", min_length=1, max_length=255)
    rtsp_url: Optional[str] = Field(None, description="RTSP URL (will be re-encrypted)", min_length=10)
    zone_id: Optional[str] = Field(None, description="Security zone UUID")
    location_name: Optional[str] = Field(None, description="Human-readable location name", max_length=255)
    latitude: Optional[float] = Field(None, description="GPS latitude coordinate", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="GPS longitude coordinate", ge=-180, le=180)


class FeedResponse(BaseModel):
    """Feed response schema"""

    id: str = Field(..., description="Feed UUID")
    name: str = Field(..., description="Feed name/identifier")
    feed_type: str = Field(..., description="Feed type")
    rtsp_url: str = Field(..., description="RTSP URL (masked for non-admin users)")
    location_name: Optional[str] = Field(None, description="Human-readable location name")
    latitude: Optional[float] = Field(None, description="GPS latitude coordinate")
    longitude: Optional[float] = Field(None, description="GPS longitude coordinate")
    zone_id: Optional[str] = Field(None, description="Security zone UUID")
    status: str = Field(..., description="Current feed status")
    resolution: Optional[str] = Field(None, description="Video resolution (e.g., 1920x1080)")
    fps: Optional[int] = Field(None, description="Frames per second")
    codec: Optional[str] = Field(None, description="Video codec (e.g., h264)")
    ai_enabled: bool = Field(..., description="AI processing enabled")
    last_active_at: Optional[str] = Field(None, description="Last time feed was active")
    created_at: str = Field(..., description="Feed creation timestamp")
    updated_at: str = Field(..., description="Feed last update timestamp")

    class Config:
        from_attributes = True


class FeedListResponse(BaseModel):
    """Feed list response schema"""

    feeds: list[FeedResponse] = Field(..., description="List of feeds")
    total: int = Field(..., description="Total number of feeds")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")


class TestConnectionRequest(BaseModel):
    """Test RTSP connection request schema"""

    rtsp_url: str = Field(..., description="RTSP URL to test", min_length=10)
    timeout: int = Field(10, description="Connection timeout in seconds", ge=1, le=60)


class TestConnectionResponse(BaseModel):
    """Test RTSP connection response schema"""

    success: bool = Field(..., description="Connection successful")
    message: str = Field(..., description="Connection result message")
    metadata: Optional[dict] = Field(None, description="Stream metadata (resolution, fps, codec)")


class FeedStatsResponse(BaseModel):
    """Feed statistics response schema (placeholder)"""

    feed_id: str = Field(..., description="Feed UUID")
    detection_count: int = Field(0, description="Total detection count")
    uptime_percentage: float = Field(0.0, description="Uptime percentage")
    avg_fps: Optional[float] = Field(None, description="Average FPS")
    fps_history: list[dict] = Field(default_factory=list, description="FPS history data points")


# ── IP Camera schemas ──────────────────────────────────────────────────────────


class IPCameraConfigRequest(BaseModel):
    """Request to configure an IP camera and register it as a feed."""

    ip: str = Field(..., description="Camera IP address (e.g. 192.168.1.64)")
    port: int = Field(554, description="RTSP port (default 554)", ge=1, le=65535)
    username: str = Field("admin", description="Camera username")
    password: str = Field("", description="Camera password")
    stream_path: Optional[str] = Field(
        None,
        description=(
            "RTSP stream path (e.g. /Streaming/Channels/101). "
            "Leave blank to auto-detect."
        ),
    )
    brand: Optional[str] = Field(
        None,
        description="Camera brand hint for faster path detection (hikvision, dahua, axis, reolink, amcrest)",
    )
    # Feed metadata
    name: str = Field(..., description="Feed name/identifier", min_length=1, max_length=255)
    zone_id: Optional[str] = Field(None, description="Security zone UUID")
    location_name: Optional[str] = Field(None, description="Human-readable location name", max_length=255)
    latitude: Optional[float] = Field(None, description="GPS latitude", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="GPS longitude", ge=-180, le=180)
    ai_enabled: bool = Field(True, description="Enable AI processing")
    auto_probe: bool = Field(
        True,
        description="Auto-probe the camera to find a working stream path before saving",
    )


class IPCameraConfigResponse(BaseModel):
    """Response after configuring an IP camera."""

    feed_id: str = Field(..., description="Created feed UUID")
    rtsp_url_masked: str = Field(..., description="Masked RTSP URL (credentials hidden)")
    stream_path: str = Field(..., description="Detected or provided stream path")
    resolution: Optional[str] = Field(None, description="Detected resolution")
    fps: Optional[float] = Field(None, description="Detected FPS")
    codec: Optional[str] = Field(None, description="Detected codec")
    probe_success: bool = Field(..., description="Whether the stream was successfully probed")
    message: str = Field(..., description="Status message")


class IPCameraDiscoverRequest(BaseModel):
    """Request to scan a subnet for IP cameras."""

    subnet: str = Field(
        "192.168.1.0/24",
        description="CIDR subnet to scan (e.g. 192.168.1.0/24)",
    )
    port: int = Field(554, description="RTSP port to check", ge=1, le=65535)
    concurrency: int = Field(50, description="Max parallel TCP checks", ge=1, le=200)


class DiscoveredCameraInfo(BaseModel):
    """Info about a discovered camera on the network."""

    ip: str = Field(..., description="Camera IP address")
    port: int = Field(..., description="Open RTSP port")
    reachable: bool = Field(..., description="Port is open/reachable")
    rtsp_url: Optional[str] = Field(None, description="Working RTSP URL (if probed)")
    stream_path: Optional[str] = Field(None, description="Working stream path")
    resolution: Optional[str] = Field(None, description="Stream resolution")
    fps: Optional[float] = Field(None, description="Stream FPS")


class IPCameraDiscoverResponse(BaseModel):
    """Response from subnet camera discovery scan."""

    subnet: str = Field(..., description="Scanned subnet")
    cameras_found: int = Field(..., description="Number of cameras found")
    cameras: list[DiscoveredCameraInfo] = Field(..., description="Discovered cameras")
