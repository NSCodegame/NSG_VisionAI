"""
Video Clip Export Service — Phase 16, Task 16.1

Exports 30-second annotated video clips around a detection event.
Retrieves the encrypted segment from MinIO, decrypts it, extracts the
clip window, overlays AI bounding boxes using OpenCV, re-encrypts, and
uploads back to MinIO. Returns a presigned download URL.
"""

import io
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.detection_event import DetectionEvent
from app.models.video_segment import VideoSegment
from app.repositories.audit_log import AuditLogRepository
from app.utils.encryption import decrypt_binary_aes_gcm, encrypt_binary_aes_gcm
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)

# Clip window: 15 seconds before and after the detection event
CLIP_WINDOW_SECONDS = 15


class ClipExportService:
    """
    Async service for exporting annotated video clips from the archive.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_repo = AuditLogRepository(session)

    async def export_clip(
        self,
        detection_event_id: UUID,
        requested_by: UUID,
        clip_window_seconds: int = CLIP_WINDOW_SECONDS,
    ) -> dict:
        """
        Export a 30-second annotated video clip around a detection event.

        Steps:
        1. Load detection event to get feed_id and frame_timestamp
        2. Find the video segment covering that timestamp
        3. Download and decrypt the segment from MinIO
        4. Extract the clip window using FFmpeg
        5. Overlay bounding boxes using OpenCV
        6. Re-encrypt and upload to MinIO
        7. Create audit log entry
        8. Return presigned download URL

        Args:
            detection_event_id: UUID of the detection event
            requested_by: UUID of the requesting user
            clip_window_seconds: Seconds before/after event (default 15 = 30s total)

        Returns:
            Dict with download_url, clip_path, expires_in_seconds
        """
        # 1. Load detection event
        event_result = await self.session.execute(
            select(DetectionEvent).where(DetectionEvent.id == detection_event_id)
        )
        event = event_result.scalar_one_or_none()

        if event is None:
            raise ValueError(f"Detection event {detection_event_id} not found")

        feed_id = event.feed_id
        event_time = event.frame_timestamp

        # 2. Find covering video segment
        segment_result = await self.session.execute(
            select(VideoSegment).where(
                VideoSegment.feed_id == feed_id,
                VideoSegment.start_timestamp <= event_time,
                VideoSegment.end_timestamp >= event_time,
            ).limit(1)
        )
        segment = segment_result.scalar_one_or_none()

        if segment is None:
            raise ValueError(
                f"No archived segment found covering event at {event_time} for feed {feed_id}"
            )

        # 3. Download and decrypt segment
        try:
            encrypted_bytes = self._download_from_minio(segment.storage_path)
            raw_bytes = decrypt_binary_aes_gcm(encrypted_bytes, settings.encryption_master_key)
        except Exception as e:
            logger.error("Failed to retrieve/decrypt segment %s: %s", segment.storage_path, e)
            raise RuntimeError(f"Segment retrieval failed: {e}") from e

        # 4. Extract clip window using FFmpeg
        offset_seconds = (event_time - segment.start_timestamp).total_seconds()
        clip_start = max(0.0, offset_seconds - clip_window_seconds)
        clip_duration = clip_window_seconds * 2

        clip_bytes = self._extract_clip_ffmpeg(raw_bytes, clip_start, clip_duration)

        # 5. Overlay bounding boxes using OpenCV
        if event.bounding_box:
            clip_bytes = self._overlay_bounding_box(
                clip_bytes,
                bounding_box=event.bounding_box,
                label=f"{event.object_class or event.detection_type} {float(event.confidence_score):.0%}",
                threat_level=event.threat_level or "LOW",
            )

        # 6. Re-encrypt and upload
        clip_id = uuid.uuid4()
        clip_path = f"clips/{feed_id}/{clip_id}.mp4.enc"

        try:
            encrypted_clip = encrypt_binary_aes_gcm(clip_bytes, settings.encryption_master_key)
            minio_client.upload_bytes(encrypted_clip, clip_path, content_type="application/octet-stream")
        except Exception as e:
            logger.error("Failed to upload clip %s: %s", clip_path, e)
            raise RuntimeError(f"Clip upload failed: {e}") from e

        # 7. Audit log
        await self.audit_repo.create(
            user_id=requested_by,
            action="VIDEO_CLIP_EXPORTED",
            resource_type="DETECTION_EVENT",
            resource_id=detection_event_id,
            details={
                "detection_event_id": str(detection_event_id),
                "feed_id": str(feed_id),
                "clip_path": clip_path,
                "event_time": event_time.isoformat(),
            },
        )
        await self.session.commit()

        # 8. Generate presigned URL (1-hour expiry)
        download_url = minio_client.get_presigned_url(clip_path, expires_in=3600)

        logger.info(
            "Clip exported: event=%s, path=%s, requested_by=%s",
            detection_event_id, clip_path, requested_by,
        )

        return {
            "clip_path": clip_path,
            "download_url": download_url,
            "expires_in_seconds": 3600,
            "detection_event_id": str(detection_event_id),
            "clip_duration_seconds": clip_duration,
        }

    def _download_from_minio(self, object_path: str) -> bytes:
        """Download an object from MinIO and return raw bytes."""
        try:
            response = minio_client.client.get_object(
                Bucket=minio_client.bucket,
                Key=object_path,
            )
            return response["Body"].read()
        except Exception as e:
            raise RuntimeError(f"MinIO download failed for {object_path}: {e}") from e

    def _extract_clip_ffmpeg(
        self, video_bytes: bytes, start_seconds: float, duration_seconds: float
    ) -> bytes:
        """
        Extract a clip from raw video bytes using FFmpeg.
        Falls back to returning the original bytes if FFmpeg is unavailable.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as in_file:
                in_file.write(video_bytes)
                in_path = in_file.name

            out_path = in_path.replace(".mp4", "_clip.mp4")

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_seconds),
                "-i", in_path,
                "-t", str(duration_seconds),
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                out_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, timeout=120
            )

            if result.returncode != 0:
                logger.warning("FFmpeg clip extraction failed: %s", result.stderr.decode())
                return video_bytes  # Fallback: return full segment

            with open(out_path, "rb") as f:
                clip_bytes = f.read()

            return clip_bytes

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("FFmpeg not available or timed out: %s", e)
            return video_bytes  # Fallback

        finally:
            for path in [in_path, out_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except OSError:
                    pass

    def _overlay_bounding_box(
        self,
        video_bytes: bytes,
        bounding_box: dict,
        label: str,
        threat_level: str,
    ) -> bytes:
        """
        Overlay AI bounding box and label on all frames of a video clip.
        Uses OpenCV for frame-by-frame annotation.
        Falls back to original bytes if OpenCV is unavailable.
        """
        try:
            import cv2
            import numpy as np

            # Threat level → BGR color
            color_map = {
                "CRITICAL": (0, 0, 255),    # Red
                "HIGH": (0, 128, 255),       # Orange
                "MEDIUM": (0, 255, 255),     # Yellow
                "LOW": (0, 255, 0),          # Green
            }
            color = color_map.get(threat_level.upper(), (128, 128, 128))

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as in_file:
                in_file.write(video_bytes)
                in_path = in_file.name

            out_path = in_path.replace(".mp4", "_annotated.mp4")

            cap = cv2.VideoCapture(in_path)
            if not cap.isOpened():
                return video_bytes

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

            # Bounding box coordinates (normalized 0.0-1.0 → pixel)
            x = int(bounding_box.get("x", 0) * width)
            y = int(bounding_box.get("y", 0) * height)
            w = int(bounding_box.get("w", 0.1) * width)
            h = int(bounding_box.get("h", 0.1) * height)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                # Draw label background
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x, y - text_h - 6), (x + text_w + 4, y), color, -1)

                # Draw label text
                cv2.putText(
                    frame, label, (x + 2, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA
                )

                out.write(frame)

            cap.release()
            out.release()

            with open(out_path, "rb") as f:
                annotated_bytes = f.read()

            return annotated_bytes

        except ImportError:
            logger.warning("OpenCV not available for bounding box overlay")
            return video_bytes

        except Exception as e:
            logger.warning("Bounding box overlay failed: %s", e)
            return video_bytes

        finally:
            for path in [in_path, out_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except OSError:
                    pass
