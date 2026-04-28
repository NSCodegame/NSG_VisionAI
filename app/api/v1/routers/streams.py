"""
HLS Stream Proxy & WebRTC Signaling — Phase 22

Provides:
  GET /streams/{feed_id}/live.m3u8  — HLS manifest
  GET /streams/{feed_id}/seg{n}.ts  — HLS segment
  POST /streams/{feed_id}/webrtc/offer — WebRTC signaling (drone feeds)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_operator
from app.core.database import get_session
from app.models.user import User
from app.repositories.video_feed import VideoFeedRepository
from app.services.hls_service import get_hls_service
from app.utils.encryption import decrypt_rtsp_url
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streams", tags=["Streaming"])


# ---------------------------------------------------------------------------
# HLS Stream Proxy
# ---------------------------------------------------------------------------


@router.get(
    "/{feed_id}/live.m3u8",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get HLS manifest",
    description="Return HLS manifest for live feed (OPERATOR+)",
)
async def get_hls_manifest(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Return the HLS .m3u8 manifest for a live video feed.

    Starts the FFmpeg transcoding process if not already running.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **feed_id**: Video feed UUID

    Returns:
    - HLS manifest (text/plain; charset=utf-8)

    Errors:
    - 404: Feed not found or offline
    - 503: Streaming service unavailable
    """
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    if feed.status == "OFFLINE":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Feed {feed_id} is offline",
        )

    # Decrypt RTSP URL
    try:
        rtsp_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
    except Exception as e:
        logger.error("Failed to decrypt RTSP URL for feed %s: %s", feed_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stream URL",
        )

    hls = get_hls_service()
    try:
        manifest = hls.generate_manifest(str(feed_id), rtsp_url)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    return PlainTextResponse(
        content=manifest,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/{feed_id}/{segment_name}",
    status_code=status.HTTP_200_OK,
    summary="Get HLS segment",
    description="Return a .ts HLS segment (OPERATOR+)",
)
async def get_hls_segment(
    request: Request,
    feed_id: UUID,
    segment_name: str = Path(..., pattern=r"^seg\d+\.ts$"),
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Return a specific HLS .ts segment for a feed.

    Requires OPERATOR role or higher.

    Path Parameters:
    - **feed_id**: Video feed UUID
    - **segment_name**: Segment filename (e.g., seg00001.ts)

    Returns:
    - MPEG-TS segment (video/mp2t)

    Errors:
    - 404: Segment not found (may have been deleted by rolling window)
    """
    hls = get_hls_service()
    segment_path = hls.get_segment_path(str(feed_id), segment_name)

    if segment_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment {segment_name} not found for feed {feed_id}",
        )

    segment_bytes = segment_path.read_bytes()

    return Response(
        content=segment_bytes,
        media_type="video/mp2t",
        headers={
            "Cache-Control": "max-age=60",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.delete(
    "/{feed_id}/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop HLS stream",
    description="Stop the HLS transcoding process for a feed (OPERATOR+)",
)
async def stop_hls_stream(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Stop the HLS transcoding process for a feed.

    Requires OPERATOR role or higher.
    """
    hls = get_hls_service()
    hls.stop_stream(str(feed_id))
    return None


# ---------------------------------------------------------------------------
# WebRTC Signaling (Phase 22.3)
# ---------------------------------------------------------------------------


@router.post(
    "/{feed_id}/webrtc/offer",
    status_code=status.HTTP_200_OK,
    summary="WebRTC offer (drone feeds)",
    description="Handle WebRTC offer for encrypted drone feed (OPERATOR+)",
)
async def webrtc_offer(
    request: Request,
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """
    Handle WebRTC SDP offer for drone feed signaling.

    Requires OPERATOR role or higher.

    Request Body:
    - **sdp**: SDP offer string
    - **type**: "offer"

    Returns:
    - SDP answer for DTLS-SRTP encrypted WebRTC connection

    Note: Full WebRTC signaling requires aiortc and a running STUN/TURN server.
    """
    body = await request.json()
    sdp_offer = body.get("sdp", "")
    offer_type = body.get("type", "offer")

    if offer_type != "offer" or not sdp_offer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must contain 'sdp' and 'type': 'offer'",
        )

    # Verify feed exists and is a drone feed
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)

    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )

    if feed.feed_type != "DRONE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feed {feed_id} is not a drone feed (type: {feed.feed_type})",
        )

    # In production: use aiortc to create RTCPeerConnection, set remote description,
    # create answer, and return SDP answer.
    # For now, return a structured response indicating signaling is ready.
    try:
        from aiortc import RTCPeerConnection, RTCSessionDescription

        pc = RTCPeerConnection()
        offer = RTCSessionDescription(sdp=sdp_offer, type=offer_type)
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "feed_id": str(feed_id),
        }

    except ImportError:
        # aiortc not installed — return a placeholder response
        logger.warning("aiortc not installed — WebRTC signaling unavailable")
        return {
            "sdp": "",
            "type": "answer",
            "feed_id": str(feed_id),
            "note": "WebRTC signaling requires aiortc. Install with: pip install aiortc",
        }
    except Exception as e:
        logger.error("WebRTC signaling failed for feed %s: %s", feed_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WebRTC signaling failed: {e}",
        )
