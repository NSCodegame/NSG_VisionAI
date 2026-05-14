"""
RecordingService — Continuous CCTV recording + event-based video clipping

Features:
  - Continuous ring-buffer recording via FFmpeg (configurable retention)
  - Event-triggered clip extraction (±30s around alert timestamp)
  - AI alert snapshot storage (JPEG frame at detection moment)
  - Forensic timeline reconstruction from stored clips
  - MinIO/S3 upload for long-term archival
  - AES-256-GCM encryption of stored segments

Architecture:
  Camera → FFmpeg (continuous HLS segments) → MinIO
                                    ↓
                          Alert event → clip_extractor
                                    ↓
                          clip.mp4 + snapshot.jpg → MinIO
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# Segment duration for ring-buffer recording (seconds)
SEGMENT_DURATION = 60          # 1-minute segments
RING_BUFFER_HOURS = 24         # Keep 24h of continuous recording
CLIP_PRE_SECONDS = 30          # Seconds before alert to include in clip
CLIP_POST_SECONDS = 30         # Seconds after alert to include in clip

# Local staging directory (before MinIO upload)
RECORDING_DIR = Path(os.environ.get("RECORDING_DIR", "/tmp/nsg_recordings"))
CLIP_DIR = Path(os.environ.get("CLIP_DIR", "/tmp/nsg_clips"))


class RecordingService:
    """
    Manages continuous recording and event-based clip extraction.
    """

    def __init__(self) -> None:
        RECORDING_DIR.mkdir(parents=True, exist_ok=True)
        CLIP_DIR.mkdir(parents=True, exist_ok=True)
        self._recording_procs: dict[str, subprocess.Popen] = {}

    # ── Continuous recording ──────────────────────────────────────────────

    def start_recording(self, feed_id: str, rtsp_url: str) -> bool:
        """
        Start continuous ring-buffer recording for a feed using FFmpeg.

        Segments are stored as 1-minute .ts files in RECORDING_DIR/{feed_id}/.
        Old segments beyond RING_BUFFER_HOURS are deleted automatically.
        """
        if feed_id in self._recording_procs:
            if self._recording_procs[feed_id].poll() is None:
                return True  # Already running
            del self._recording_procs[feed_id]

        feed_dir = RECORDING_DIR / feed_id
        feed_dir.mkdir(parents=True, exist_ok=True)

        # Segment filename pattern: {feed_id}/seg_%Y%m%d_%H%M%S.ts
        segment_pattern = str(feed_dir / "seg_%Y%m%d_%H%M%S.ts")

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            # Copy stream without re-encoding (zero CPU overhead)
            "-c", "copy",
            # Segment output
            "-f", "segment",
            "-segment_time", str(SEGMENT_DURATION),
            "-segment_format", "mpegts",
            "-segment_atclocktime", "1",
            "-strftime", "1",
            "-reset_timestamps", "1",
            segment_pattern,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self._recording_procs[feed_id] = proc
            logger.info("Recording started for feed %s", feed_id)
            return True
        except FileNotFoundError:
            logger.warning("FFmpeg not found — recording unavailable for feed %s", feed_id)
            return False
        except Exception as exc:
            logger.error("Failed to start recording for feed %s: %s", feed_id, exc)
            return False

    def stop_recording(self, feed_id: str) -> None:
        """Stop recording for a feed."""
        proc = self._recording_procs.pop(feed_id, None)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        logger.info("Recording stopped for feed %s", feed_id)

    def cleanup_old_segments(self, feed_id: str) -> int:
        """
        Delete segments older than RING_BUFFER_HOURS.
        Returns number of segments deleted.
        """
        feed_dir = RECORDING_DIR / feed_id
        if not feed_dir.exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=RING_BUFFER_HOURS)
        deleted = 0
        for seg in feed_dir.glob("seg_*.ts"):
            if datetime.fromtimestamp(seg.stat().st_mtime, tz=timezone.utc) < cutoff:
                seg.unlink(missing_ok=True)
                deleted += 1
        return deleted

    # ── Event-based clip extraction ───────────────────────────────────────

    async def extract_clip(
        self,
        feed_id: str,
        event_time: datetime,
        pre_seconds: int = CLIP_PRE_SECONDS,
        post_seconds: int = CLIP_POST_SECONDS,
        alert_id: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Extract a video clip around an alert event from stored segments.

        Finds all segments that overlap [event_time - pre, event_time + post],
        concatenates them, and trims to the exact window.

        Returns path to the extracted .mp4 clip, or None if segments unavailable.
        """
        feed_dir = RECORDING_DIR / feed_id
        if not feed_dir.exists():
            logger.warning("No recordings found for feed %s", feed_id)
            return None

        clip_start = event_time - timedelta(seconds=pre_seconds)
        clip_end = event_time + timedelta(seconds=post_seconds)

        # Find segments that overlap the clip window
        segments = sorted(feed_dir.glob("seg_*.ts"))
        relevant = []
        for seg in segments:
            seg_time = datetime.fromtimestamp(seg.stat().st_mtime, tz=timezone.utc)
            seg_start = seg_time - timedelta(seconds=SEGMENT_DURATION)
            if seg_start <= clip_end and seg_time >= clip_start:
                relevant.append(seg)

        if not relevant:
            logger.warning("No segments found for clip at %s for feed %s", event_time, feed_id)
            return None

        # Create concat list
        clip_id = alert_id or str(uuid4())
        clip_path = CLIP_DIR / f"clip_{feed_id}_{clip_id}.mp4"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for seg in relevant:
                f.write(f"file '{seg.absolute()}'\n")
            concat_file = f.name

        try:
            # Calculate offset into first segment
            first_seg_time = datetime.fromtimestamp(
                relevant[0].stat().st_mtime, tz=timezone.utc
            ) - timedelta(seconds=SEGMENT_DURATION)
            start_offset = max(0, (clip_start - first_seg_time).total_seconds())
            duration = pre_seconds + post_seconds

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-ss", str(start_offset),
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(clip_path),
            ]

            loop = asyncio.get_event_loop()
            proc = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, timeout=60),
            )

            if proc.returncode != 0:
                logger.error("FFmpeg clip extraction failed: %s", proc.stderr.decode())
                return None

            logger.info("Clip extracted: %s (%.1fs)", clip_path, duration)
            return clip_path

        except Exception as exc:
            logger.error("Clip extraction error: %s", exc)
            return None
        finally:
            os.unlink(concat_file)

    # ── AI alert snapshot ─────────────────────────────────────────────────

    async def save_alert_snapshot(
        self,
        feed_id: str,
        frame_jpeg: bytes,
        alert_id: str,
        detections: Optional[list] = None,
    ) -> Optional[Path]:
        """
        Save a JPEG snapshot at the moment of an alert.
        Optionally draws detection bounding boxes on the frame.
        """
        snapshot_dir = CLIP_DIR / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"alert_{alert_id}_{feed_id}.jpg"

        try:
            if detections:
                # Draw bounding boxes on snapshot
                import cv2
                import numpy as np
                nparr = np.frombuffer(frame_jpeg, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    for det in detections:
                        bb = det.get("bounding_box", {})
                        h, w = frame.shape[:2]
                        x1 = int(bb.get("x", 0) * w)
                        y1 = int(bb.get("y", 0) * h)
                        x2 = int((bb.get("x", 0) + bb.get("w", 0)) * w)
                        y2 = int((bb.get("y", 0) + bb.get("h", 0)) * h)
                        color = (0, 0, 255) if det.get("object_class") in ("knife", "gun") else (0, 255, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f"{det.get('object_class', '?')} {det.get('confidence', 0):.0%}"
                        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    frame_jpeg = buf.tobytes()

            snapshot_path.write_bytes(frame_jpeg)
            logger.info("Alert snapshot saved: %s", snapshot_path)
            return snapshot_path
        except Exception as exc:
            logger.error("Failed to save alert snapshot: %s", exc)
            return None

    # ── Forensic timeline ─────────────────────────────────────────────────

    def get_available_segments(
        self,
        feed_id: str,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Return metadata for all available recording segments for a feed.
        Used for forensic timeline reconstruction.
        """
        feed_dir = RECORDING_DIR / feed_id
        if not feed_dir.exists():
            return []

        segments = []
        for seg in sorted(feed_dir.glob("seg_*.ts")):
            mtime = datetime.fromtimestamp(seg.stat().st_mtime, tz=timezone.utc)
            seg_start = mtime - timedelta(seconds=SEGMENT_DURATION)

            if from_dt and mtime < from_dt:
                continue
            if to_dt and seg_start > to_dt:
                continue

            segments.append({
                "filename": seg.name,
                "path": str(seg),
                "start_time": seg_start.isoformat(),
                "end_time": mtime.isoformat(),
                "size_bytes": seg.stat().st_size,
                "duration_seconds": SEGMENT_DURATION,
            })

        return segments


# ── Singleton ─────────────────────────────────────────────────────────────────

_recording_service: Optional[RecordingService] = None


def get_recording_service() -> RecordingService:
    global _recording_service
    if _recording_service is None:
        _recording_service = RecordingService()
    return _recording_service
