"""Video Feed management endpoints"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_admin, require_operator
from app.api.v1.schemas.feed import (
    CreateFeedRequest,
    DiscoveredCameraInfo,
    FeedListResponse,
    FeedResponse,
    FeedStatsResponse,
    IPCameraConfigRequest,
    IPCameraConfigResponse,
    IPCameraDiscoverRequest,
    IPCameraDiscoverResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    UpdateFeedRequest,
)
from app.core.database import get_session
from app.models.user import User, UserRole
from app.models.video_feed import FeedStatus, FeedType, VideoFeed
from app.repositories.video_feed import VideoFeedRepository
from app.services.feed_service import FeedService
from app.services.transcoding_service import get_transcoding_service
from app.utils.encryption import decrypt_rtsp_url
from app.utils.ip_camera import (
    build_rtsp_url,
    probe_camera,
    scan_subnet_for_cameras,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feeds", tags=["Video Feeds"])


def _extract_ip_address(request: Request) -> Optional[str]:
    """Extract IP address from request"""
    return request.client.host if request.client else None


def _mask_rtsp_url(user: User, rtsp_url_encrypted: str) -> str:
    """
    Mask RTSP URL for non-admin users.

    Args:
        user: Current user
        rtsp_url_encrypted: Encrypted RTSP URL

    Returns:
        Masked URL for non-admin, encrypted indicator for admin
    """
    user_role = UserRole(user.role)

    if user_role == UserRole.ADMIN:
        # Admin users see encrypted indicator
        return "[ENCRYPTED]"
    else:
        # Non-admin users see masked URL
        return "rtsp://***:***@***:***/**"


@router.get(
    "",
    response_model=FeedListResponse,
    status_code=status.HTTP_200_OK,
    summary="List video feeds",
    description="List video feeds with filtering and pagination (OPERATOR+)",
)
async def list_feeds(
    request: Request,
    feed_type: Optional[FeedType] = Query(None, description="Filter by feed type"),
    zone_id: Optional[str] = Query(None, description="Filter by zone UUID"),
    status_filter: Optional[FeedStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    List video feeds with optional filtering and pagination.

    Requires OPERATOR role or higher.

    Query Parameters:
    - **feed_type**: Filter by feed type (FIXED_CAMERA, DRONE, BODY_CAM, LEGACY_CCTV)
    - **zone_id**: Filter by security zone UUID
    - **status**: Filter by status (ACTIVE, OFFLINE, DEGRADED, MAINTENANCE)
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records (default: 100, max: 1000)

    Returns:
    - List of feeds with pagination metadata
    - RTSP URLs are masked for non-admin users
    """
    feed_service = FeedService(session)

    # Parse zone_id if provided
    zone_uuid = None
    if zone_id:
        try:
            zone_uuid = UUID(zone_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid zone_id format: {zone_id}",
            )

    # Get feeds with filters
    feeds = await feed_service.get_feeds(
        feed_type=feed_type,
        zone_id=zone_uuid,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

    # Count total feeds with same filters
    filters = []
    if feed_type is not None:
        filters.append(VideoFeed.feed_type == feed_type.value)
    if zone_uuid is not None:
        filters.append(VideoFeed.zone_id == zone_uuid)
    if status_filter is not None:
        filters.append(VideoFeed.status == status_filter.value)

    feed_repo = VideoFeedRepository(session)
    total = await feed_repo.count(filters=filters if filters else None)

    # Convert to response schema with masked RTSP URLs
    feed_responses = [
        FeedResponse(
            id=str(feed.id),
            name=feed.name,
            feed_type=feed.feed_type,
            rtsp_url=_mask_rtsp_url(current_user, feed.rtsp_url_encrypted),
            location_name=feed.location_name,
            latitude=float(feed.latitude) if feed.latitude else None,
            longitude=float(feed.longitude) if feed.longitude else None,
            zone_id=str(feed.zone_id) if feed.zone_id else None,
            status=feed.status,
            resolution=feed.resolution,
            fps=feed.fps,
            codec=feed.codec,
            ai_enabled=feed.ai_enabled,
            last_active_at=feed.last_active_at.isoformat() if feed.last_active_at else None,
            created_at=feed.created_at.isoformat(),
            updated_at=feed.updated_at.isoformat(),
        )
        for feed in feeds
    ]

    return FeedListResponse(
        feeds=feed_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=FeedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create video feed",
    description="Create new video feed with encrypted RTSP URL (ADMIN only)",
)
async def create_feed(
    request: Request,
    feed_data: CreateFeedRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Create new video feed.

    Requires ADMIN role.

    Request Body:
    - **name**: Feed name/identifier
    - **feed_type**: Feed type (FIXED_CAMERA, DRONE, BODY_CAM, LEGACY_CCTV)
    - **rtsp_url**: RTSP URL (will be encrypted before storage)
    - **zone_id**: Security zone UUID (optional)
    - **location_name**: Human-readable location name (optional)
    - **latitude**: GPS latitude coordinate (optional)
    - **longitude**: GPS longitude coordinate (optional)
    - **ai_enabled**: Enable AI processing (default: true)

    Returns:
    - Created feed details
    - RTSP URL is masked in response

    Errors:
    - 400: Invalid RTSP URL format or zone_id
    """
    feed_service = FeedService(session)
    ip_address = _extract_ip_address(request)

    # Parse zone_id if provided
    zone_uuid = None
    if feed_data.zone_id:
        try:
            zone_uuid = UUID(feed_data.zone_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid zone_id format: {feed_data.zone_id}",
            )

    try:
        feed = await feed_service.create_feed(
            name=feed_data.name,
            feed_type=feed_data.feed_type,
            rtsp_url=feed_data.rtsp_url,
            zone_id=zone_uuid,
            location_name=feed_data.location_name,
            latitude=feed_data.latitude,
            longitude=feed_data.longitude,
            ai_enabled=feed_data.ai_enabled,
            created_by=current_user.id,
            ip_address=ip_address,
        )

        return FeedResponse(
            id=str(feed.id),
            name=feed.name,
            feed_type=feed.feed_type,
            rtsp_url=_mask_rtsp_url(current_user, feed.rtsp_url_encrypted),
            location_name=feed.location_name,
            latitude=float(feed.latitude) if feed.latitude else None,
            longitude=float(feed.longitude) if feed.longitude else None,
            zone_id=str(feed.zone_id) if feed.zone_id else None,
            status=feed.status,
            resolution=feed.resolution,
            fps=feed.fps,
            codec=feed.codec,
            ai_enabled=feed.ai_enabled,
            last_active_at=feed.last_active_at.isoformat() if feed.last_active_at else None,
            created_at=feed.created_at.isoformat(),
            updated_at=feed.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{feed_id}",
    response_model=FeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get feed details",
    description="Get video feed details by ID (OPERATOR+)",
)
async def get_feed(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get video feed details by ID.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **feed_id**: Feed UUID

    Returns:
    - Feed details
    - RTSP URL is masked for non-admin users

    Errors:
    - 404: Feed not found
    """
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    return FeedResponse(
        id=str(feed.id),
        name=feed.name,
        feed_type=feed.feed_type,
        rtsp_url=_mask_rtsp_url(current_user, feed.rtsp_url_encrypted),
        location_name=feed.location_name,
        latitude=float(feed.latitude) if feed.latitude else None,
        longitude=float(feed.longitude) if feed.longitude else None,
        zone_id=str(feed.zone_id) if feed.zone_id else None,
        status=feed.status,
        resolution=feed.resolution,
        fps=feed.fps,
        codec=feed.codec,
        ai_enabled=feed.ai_enabled,
        last_active_at=feed.last_active_at.isoformat() if feed.last_active_at else None,
        created_at=feed.created_at.isoformat(),
        updated_at=feed.updated_at.isoformat(),
    )


@router.put(
    "/{feed_id}",
    response_model=FeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Update feed",
    description="Update video feed details (ADMIN only)",
)
async def update_feed(
    request: Request,
    feed_id: UUID,
    feed_data: UpdateFeedRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Update video feed details.

    Requires ADMIN role.

    Path Parameters:
    - **feed_id**: Feed UUID

    Request Body (all fields optional for partial updates):
    - **name**: Feed name/identifier
    - **rtsp_url**: RTSP URL (will be re-encrypted)
    - **zone_id**: Security zone UUID
    - **location_name**: Human-readable location name
    - **latitude**: GPS latitude coordinate
    - **longitude**: GPS longitude coordinate

    Returns:
    - Updated feed details
    - RTSP URL is masked in response

    Errors:
    - 404: Feed not found
    - 400: Invalid RTSP URL format or zone_id
    """
    feed_repo = VideoFeedRepository(session)
    ip_address = _extract_ip_address(request)

    # Check if feed exists
    feed = await feed_repo.get(feed_id)
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    # Parse zone_id if provided
    zone_uuid = None
    if feed_data.zone_id:
        try:
            zone_uuid = UUID(feed_data.zone_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid zone_id format: {feed_data.zone_id}",
            )

    feed_service = FeedService(session)

    try:
        feed = await feed_service.update_feed(
            feed_id=feed_id,
            name=feed_data.name,
            rtsp_url=feed_data.rtsp_url,
            zone_id=zone_uuid,
            location_name=feed_data.location_name,
            latitude=feed_data.latitude,
            longitude=feed_data.longitude,
            updated_by=current_user.id,
            ip_address=ip_address,
        )

        if feed is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feed {feed_id} not found",
            )

        return FeedResponse(
            id=str(feed.id),
            name=feed.name,
            feed_type=feed.feed_type,
            rtsp_url=_mask_rtsp_url(current_user, feed.rtsp_url_encrypted),
            location_name=feed.location_name,
            latitude=float(feed.latitude) if feed.latitude else None,
            longitude=float(feed.longitude) if feed.longitude else None,
            zone_id=str(feed.zone_id) if feed.zone_id else None,
            status=feed.status,
            resolution=feed.resolution,
            fps=feed.fps,
            codec=feed.codec,
            ai_enabled=feed.ai_enabled,
            last_active_at=feed.last_active_at.isoformat() if feed.last_active_at else None,
            created_at=feed.created_at.isoformat(),
            updated_at=feed.updated_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{feed_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete feed",
    description="Soft delete video feed (set status to MAINTENANCE) (ADMIN only)",
)
async def delete_feed(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Soft delete video feed (set status to MAINTENANCE and disable AI).

    Requires ADMIN role.

    Path Parameters:
    - **feed_id**: Feed UUID

    Returns:
    - 204 No Content on success

    Errors:
    - 404: Feed not found
    """
    feed_service = FeedService(session)
    ip_address = _extract_ip_address(request)

    feed = await feed_service.delete_feed(
        feed_id=feed_id,
        deleted_by=current_user.id,
        ip_address=ip_address,
    )

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    return None


@router.post(
    "/{feed_id}/toggle-ai",
    response_model=FeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle AI processing",
    description="Toggle AI processing for video feed (OPERATOR+)",
)
async def toggle_ai_processing(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Toggle AI processing flag for video feed.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **feed_id**: Feed UUID

    Returns:
    - Updated feed details with toggled ai_enabled flag
    - RTSP URL is masked for non-admin users

    Errors:
    - 404: Feed not found
    """
    feed_service = FeedService(session)
    ip_address = _extract_ip_address(request)

    feed = await feed_service.toggle_ai_processing(
        feed_id=feed_id,
        toggled_by=current_user.id,
        ip_address=ip_address,
    )

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    return FeedResponse(
        id=str(feed.id),
        name=feed.name,
        feed_type=feed.feed_type,
        rtsp_url=_mask_rtsp_url(current_user, feed.rtsp_url_encrypted),
        location_name=feed.location_name,
        latitude=float(feed.latitude) if feed.latitude else None,
        longitude=float(feed.longitude) if feed.longitude else None,
        zone_id=str(feed.zone_id) if feed.zone_id else None,
        status=feed.status,
        resolution=feed.resolution,
        fps=feed.fps,
        codec=feed.codec,
        ai_enabled=feed.ai_enabled,
        last_active_at=feed.last_active_at.isoformat() if feed.last_active_at else None,
        created_at=feed.created_at.isoformat(),
        updated_at=feed.updated_at.isoformat(),
    )


@router.post(
    "/test",
    response_model=TestConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Test RTSP connection",
    description="Test RTSP connection before saving (ADMIN only)",
)
async def test_connection(
    request: Request,
    test_data: TestConnectionRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Test RTSP connection using OpenCV VideoCapture.

    Requires ADMIN role.

    Request Body:
    - **rtsp_url**: RTSP URL to test
    - **timeout**: Connection timeout in seconds (default: 10, max: 60)

    Returns:
    - Connection success status
    - Result message
    - Stream metadata (resolution, fps, codec) if successful

    Note: This endpoint does not save the feed, only tests the connection.
    """
    feed_service = FeedService(session)

    result = await feed_service.test_connection(
        rtsp_url=test_data.rtsp_url,
        timeout=test_data.timeout,
    )

    return TestConnectionResponse(
        success=result["success"],
        message=result["message"],
        metadata=result["metadata"],
    )


@router.get(
    "/{feed_id}/stats",
    response_model=FeedStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get feed statistics",
    description="Get video feed statistics (OPERATOR+)",
)
async def get_feed_stats(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get video feed statistics.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **feed_id**: Feed UUID

    Returns:
    - Detection counts
    - Uptime percentage
    - FPS history

    Note: This is a placeholder implementation. Full statistics will be
    implemented when detection events and monitoring are in place.

    Errors:
    - 404: Feed not found
    """
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    # Placeholder implementation
    # TODO: Implement real statistics from detection_events and monitoring data
    return FeedStatsResponse(
        feed_id=str(feed_id),
        detection_count=0,
        uptime_percentage=0.0,
        avg_fps=feed.fps if feed.fps else None,
        fps_history=[],
    )


@router.get(
    "/{feed_id}/stream",
    status_code=status.HTTP_200_OK,
    summary="Get HLS stream URL",
    description="Trigger transcoding and get the .m3u8 playlist URL for a feed (OPERATOR+)",
)
async def get_feed_stream(
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Get the HLS stream URL for a video feed.
    Starts the FFmpeg transcoder if not already running.
    """
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    # Decrypt RTSP URL for FFmpeg
    from app.core.config import settings
    try:
        # In a real impl, we use the encryption service
        # rtsp_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.secret_key)
        rtsp_url = "rtsp://mock-url:554/live" # Default for dev/mock
    except Exception as e:
        logger.error("Failed to decrypt RTSP URL for feed %s: %s", feed_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stream credentials"
        )

    transcoder = get_transcoding_service()
    playlist_path = await transcoder.start_transcoding(feed_id, rtsp_url)
    
    # Return the relative URL for the frontend to consume
    # This assumes we are serving the 'streams' directory via FastAPI or Nginx
    return {"stream_url": f"/streams/{feed_id}/index.m3u8"}


# ── IP Camera endpoints ────────────────────────────────────────────────────────


@router.post(
    "/ip-camera/configure",
    response_model=IPCameraConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure IP camera",
    description=(
        "Register an IP camera by IP address and credentials. "
        "Optionally auto-probes the camera to find a working RTSP stream path "
        "before saving. (ADMIN only)"
    ),
)
async def configure_ip_camera(
    request: Request,
    camera_data: IPCameraConfigRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Configure and register an IP camera as a video feed.

    Workflow:
    1. If ``auto_probe=true`` (default), the server connects to the camera and
       tries common RTSP stream paths to find one that works.
    2. The working RTSP URL (or the manually supplied one) is encrypted and
       stored as a new VideoFeed record with type ``IP_CAMERA``.
    3. Returns the created feed ID and masked RTSP URL.

    Request Body:
    - **ip**: Camera IP address
    - **port**: RTSP port (default 554)
    - **username** / **password**: Camera credentials
    - **stream_path**: Explicit path — skip auto-probe if provided
    - **brand**: Brand hint (hikvision, dahua, axis, reolink, amcrest)
    - **name**: Feed display name
    - **auto_probe**: Try to detect stream path automatically (default true)

    Errors:
    - 400: Invalid IP, no working stream found, or validation failure
    - 403: Insufficient role
    """
    ip_address = _extract_ip_address(request)

    # Determine stream path — explicit or auto-probed
    stream_path = camera_data.stream_path
    probe_success = False
    resolution = None
    fps_val = None
    codec_val = None

    if camera_data.auto_probe and not stream_path:
        # Probe the camera to find a working path
        discovered = await probe_camera(
            ip=camera_data.ip,
            port=camera_data.port,
            username=camera_data.username,
            password=camera_data.password,
            brand=camera_data.brand,
            timeout=10,
        )
        if discovered is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Could not find a working RTSP stream on {camera_data.ip}:{camera_data.port}. "
                    "Check the IP, credentials, and that the camera is reachable. "
                    "You can also supply stream_path manually to skip auto-probe."
                ),
            )
        stream_path = discovered.stream_path
        probe_success = True
        resolution = discovered.resolution
        fps_val = discovered.fps
        codec_val = discovered.codec
    else:
        # Use provided path or default
        stream_path = stream_path or "/stream1"
        probe_success = False

    # Build the full RTSP URL
    rtsp_url = build_rtsp_url(
        ip=camera_data.ip,
        port=camera_data.port,
        username=camera_data.username,
        password=camera_data.password,
        stream_path=stream_path,
    )

    # Parse zone_id
    zone_uuid = None
    if camera_data.zone_id:
        try:
            zone_uuid = UUID(camera_data.zone_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid zone_id format: {camera_data.zone_id}",
            )

    # Create the feed record
    feed_service = FeedService(session)
    try:
        feed = await feed_service.create_feed(
            name=camera_data.name,
            feed_type=FeedType.IP_CAMERA,
            rtsp_url=rtsp_url,
            zone_id=zone_uuid,
            location_name=camera_data.location_name,
            latitude=camera_data.latitude,
            longitude=camera_data.longitude,
            ai_enabled=camera_data.ai_enabled,
            created_by=current_user.id,
            ip_address=ip_address,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Update stream metadata if we probed it
    if probe_success and (resolution or fps_val or codec_val):
        feed_repo = VideoFeedRepository(session)
        update_kwargs: dict = {}
        if resolution:
            update_kwargs["resolution"] = resolution
        if fps_val:
            update_kwargs["fps"] = int(fps_val)
        if codec_val:
            update_kwargs["codec"] = codec_val
        if update_kwargs:
            await feed_repo.update(feed.id, **update_kwargs)
            await session.commit()

    # Mask credentials in the returned URL
    masked_url = f"rtsp://***:***@{camera_data.ip}:{camera_data.port}{stream_path}"

    return IPCameraConfigResponse(
        feed_id=str(feed.id),
        rtsp_url_masked=masked_url,
        stream_path=stream_path,
        resolution=resolution,
        fps=fps_val,
        codec=codec_val,
        probe_success=probe_success,
        message=(
            f"IP camera registered successfully. "
            f"{'Stream path auto-detected.' if probe_success else 'Stream path set manually.'}"
        ),
    )


@router.post(
    "/ip-camera/discover",
    response_model=IPCameraDiscoverResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover IP cameras on subnet",
    description=(
        "Scan a subnet for hosts with an open RTSP port (TCP 554). "
        "Returns a list of reachable camera IPs. (ADMIN only)"
    ),
)
async def discover_ip_cameras(
    request: Request,
    discover_data: IPCameraDiscoverRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Scan a subnet for IP cameras.

    Performs a fast TCP port scan on the given subnet. Hosts with the RTSP
    port open are returned as potential cameras. This does NOT attempt to
    open streams or authenticate — use ``/feeds/ip-camera/configure`` for that.

    Request Body:
    - **subnet**: CIDR subnet (e.g. "192.168.1.0/24")
    - **port**: RTSP port to check (default 554)
    - **concurrency**: Parallel TCP checks (default 50, max 200)

    Returns:
    - List of IPs with the RTSP port open

    Note: Scanning large subnets (/16 or bigger) may take a long time.
    Stick to /24 or smaller for interactive use.

    Errors:
    - 400: Invalid subnet format
    - 403: Insufficient role
    """
    import ipaddress

    # Validate subnet
    try:
        network = ipaddress.ip_network(discover_data.subnet, strict=False)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subnet format: {discover_data.subnet}",
        )

    # Guard against accidentally scanning huge ranges interactively
    if network.num_addresses > 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Subnet {discover_data.subnet} has {network.num_addresses} addresses. "
                "Limit discovery scans to /22 or smaller (≤1024 hosts)."
            ),
        )

    discovered = await scan_subnet_for_cameras(
        subnet=discover_data.subnet,
        port=discover_data.port,
        concurrency=discover_data.concurrency,
    )

    cameras = [
        DiscoveredCameraInfo(
            ip=cam.ip,
            port=cam.port,
            reachable=cam.reachable,
            rtsp_url=cam.rtsp_url,
            stream_path=cam.stream_path,
            resolution=cam.resolution,
            fps=cam.fps,
        )
        for cam in discovered
    ]

    return IPCameraDiscoverResponse(
        subnet=discover_data.subnet,
        cameras_found=len(cameras),
        cameras=cameras,
    )
