"""
Recording & Forensic Timeline API

Endpoints:
  POST /recording/{feed_id}/start     — Start continuous recording
  DELETE /recording/{feed_id}/stop    — Stop recording
  GET  /recording/{feed_id}/segments  — List available segments (forensic timeline)
  POST /recording/{feed_id}/clip      — Extract clip around a timestamp
  GET  /recording/clips/{alert_id}    — Get clip download URL
  GET  /recording/snapshots/{alert_id} — Get alert snapshot
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import require_analyst, require_operator
from app.core.database import get_session
from app.models.user import User
from app.repositories.video_feed import VideoFeedRepository
from app.services.recording_service import get_recording_service, CLIP_DIR
from app.tasks.recording_tasks import extract_alert_clip
from app.utils.encryption import decrypt_rtsp_url
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recording", tags=["Recording & Forensics"])


class ClipRequest(BaseModel):
    event_time: str          # ISO 8601 datetime
    alert_id: Optional[str] = None
    pre_seconds: int = 30
    post_seconds: int = 30


# ── Recording lifecycle ───────────────────────────────────────────────────────


@router.post("/{feed_id}/start", status_code=status.HTTP_200_OK,
             summary="Start continuous recording")
async def start_recording(
    feed_id: UUID,
    current_user: User = Depends(require_operator),
    session: AsyncSession = Depends(get_session),
):
    """Start continuous ring-buffer recording for a feed (OPERATOR+)."""
    feed_repo = VideoFeedRepository(session)
    feed = await feed_repo.get(feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")

    try:
        rtsp_url = decrypt_rtsp_url(feed.rtsp_url_encrypted, settings.encryption_master_key)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt stream URL")

    service = get_recording_service()
    ok = service.start_recording(str(feed_id), rtsp_url)
    if not ok:
        raise HTTPException(status_code=503, detail="FFmpeg not available — recording requires FFmpeg")

    return {"status": "recording_started", "feed_id": str(feed_id)}


@router.delete("/{feed_id}/stop", status_code=status.HTTP_204_NO_CONTENT,
               summary="Stop recording")
async def stop_recording(
    feed_id: UUID,
    current_user: User = Depends(require_operator),
):
    """Stop continuous recording for a feed (OPERATOR+)."""
    get_recording_service().stop_recording(str(feed_id))
    return None


# ── Forensic timeline ─────────────────────────────────────────────────────────


@router.get("/{feed_id}/segments", summary="List recording segments (forensic timeline)")
async def list_segments(
    feed_id: UUID,
    from_dt: Optional[str] = Query(None, description="ISO 8601 start datetime"),
    to_dt: Optional[str] = Query(None, description="ISO 8601 end datetime"),
    current_user: User = Depends(require_analyst),
):
    """
    List all available recording segments for a feed within a time range.
    Used for forensic timeline reconstruction. (ANALYST+)
    """
    from_datetime = datetime.fromisoformat(from_dt) if from_dt else None
    to_datetime = datetime.fromisoformat(to_dt) if to_dt else None

    service = get_recording_service()
    segments = service.get_available_segments(str(feed_id), from_datetime, to_datetime)

    return {
        "feed_id": str(feed_id),
        "segment_count": len(segments),
        "segments": segments,
    }


# ── Clip extraction ───────────────────────────────────────────────────────────


@router.post("/{feed_id}/clip", status_code=status.HTTP_202_ACCEPTED,
             summary="Extract video clip around an event")
async def request_clip(
    feed_id: UUID,
    req: ClipRequest,
    current_user: User = Depends(require_analyst),
):
    """
    Queue a clip extraction task for an event timestamp. (ANALYST+)
    Returns a task ID to poll for completion.
    """
    import uuid
    alert_id = req.alert_id or str(uuid.uuid4())

    task = extract_alert_clip.delay(
        feed_id=str(feed_id),
        event_time_iso=req.event_time,
        alert_id=alert_id,
        pre_seconds=req.pre_seconds,
        post_seconds=req.post_seconds,
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "alert_id": alert_id,
        "feed_id": str(feed_id),
        "message": "Clip extraction queued. Poll /recording/clips/{alert_id} for result.",
    }


@router.get("/clips/{alert_id}", summary="Download extracted clip")
async def get_clip(
    alert_id: str,
    feed_id: str = Query(..., description="Feed UUID"),
    current_user: User = Depends(require_analyst),
):
    """
    Download an extracted video clip. (ANALYST+)
    Returns 404 if clip not yet ready or not found.
    """
    # Search for clip file
    import glob
    pattern = str(CLIP_DIR / f"clip_{feed_id}_{alert_id}.mp4")
    matches = glob.glob(pattern)

    if not matches:
        raise HTTPException(
            status_code=404,
            detail="Clip not found. It may still be processing or segments were unavailable.",
        )

    return FileResponse(
        path=matches[0],
        media_type="video/mp4",
        filename=f"nsg_clip_{alert_id}.mp4",
        headers={"Content-Disposition": f'attachment; filename="nsg_clip_{alert_id}.mp4"'},
    )


@router.get("/snapshots/{alert_id}", summary="Get alert snapshot")
async def get_snapshot(
    alert_id: str,
    feed_id: str = Query(..., description="Feed UUID"),
    current_user: User = Depends(require_analyst),
):
    """
    Get the annotated JPEG snapshot saved at alert moment. (ANALYST+)
    """
    snapshot_path = CLIP_DIR / "snapshots" / f"alert_{alert_id}_{feed_id}.jpg"

    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return FileResponse(
        path=str(snapshot_path),
        media_type="image/jpeg",
        filename=f"nsg_alert_{alert_id}.jpg",
    )
