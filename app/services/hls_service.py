"""
HLS Stream Service — Phase 22, Task 22.1

Manages low-latency HLS stream generation from RTSP feeds using FFmpeg.
Serves .m3u8 manifests and .ts segments for browser-native playback.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# HLS segment settings
HLS_SEGMENT_DURATION = 2       # seconds per segment (low-latency)
HLS_LIST_SIZE = 5              # segments in playlist
HLS_BASE_DIR = Path(os.environ.get("HLS_STREAM_DIR", "/tmp/nsg_hls"))


class HLSService:
    """
    Manages FFmpeg processes that transcode RTSP streams to HLS.
    One process per active feed.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or HLS_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._processes: Dict[str, subprocess.Popen] = {}

    # ------------------------------------------------------------------
    # Stream lifecycle
    # ------------------------------------------------------------------

    def start_stream(self, feed_id: str, rtsp_url: str) -> Path:
        """
        Start an FFmpeg HLS transcoding process for a feed.

        Args:
            feed_id: Feed UUID string
            rtsp_url: Decrypted RTSP URL

        Returns:
            Path to the .m3u8 manifest file
        """
        if feed_id in self._processes:
            proc = self._processes[feed_id]
            if proc.poll() is None:
                return self._manifest_path(feed_id)
            # Process died — clean up and restart
            self._cleanup_process(feed_id)

        feed_dir = self.base_dir / feed_id
        feed_dir.mkdir(parents=True, exist_ok=True)
        manifest = feed_dir / "live.m3u8"

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            # Video: H.264 fast encode
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-g", "30",           # keyframe every 30 frames
            "-sc_threshold", "0",
            # Audio: AAC
            "-c:a", "aac",
            "-ar", "44100",
            "-b:a", "64k",
            # HLS output
            "-f", "hls",
            "-hls_time", str(HLS_SEGMENT_DURATION),
            "-hls_list_size", str(HLS_LIST_SIZE),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(feed_dir / "seg%05d.ts"),
            str(manifest),
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self._processes[feed_id] = proc
            logger.info("HLS stream started for feed %s (pid=%d)", feed_id, proc.pid)
            return manifest
        except FileNotFoundError:
            logger.warning("FFmpeg not found — HLS streaming unavailable for feed %s", feed_id)
            raise RuntimeError("FFmpeg is not installed. HLS streaming requires FFmpeg.")
        except Exception as e:
            logger.error("Failed to start HLS for feed %s: %s", feed_id, e)
            raise

    def stop_stream(self, feed_id: str) -> None:
        """Stop the HLS transcoding process for a feed."""
        self._cleanup_process(feed_id)
        logger.info("HLS stream stopped for feed %s", feed_id)

    def stop_all(self) -> None:
        """Stop all active HLS processes (called on shutdown)."""
        for feed_id in list(self._processes.keys()):
            self._cleanup_process(feed_id)

    def is_running(self, feed_id: str) -> bool:
        """Check if an HLS process is active for a feed."""
        proc = self._processes.get(feed_id)
        return proc is not None and proc.poll() is None

    # ------------------------------------------------------------------
    # Manifest / segment access
    # ------------------------------------------------------------------

    def get_manifest_path(self, feed_id: str) -> Optional[Path]:
        """Return the manifest path if it exists."""
        path = self._manifest_path(feed_id)
        return path if path.exists() else None

    def get_segment_path(self, feed_id: str, segment_name: str) -> Optional[Path]:
        """Return the path to a specific .ts segment if it exists."""
        # Sanitize segment name to prevent path traversal
        safe_name = Path(segment_name).name
        if not safe_name.endswith(".ts"):
            return None
        path = self.base_dir / feed_id / safe_name
        return path if path.exists() else None

    def generate_manifest(self, feed_id: str, rtsp_url: str) -> str:
        """
        Generate an HLS manifest string.
        Starts the FFmpeg process if not already running.

        Returns:
            HLS manifest content as string
        """
        if not self.is_running(feed_id):
            try:
                self.start_stream(feed_id, rtsp_url)
            except RuntimeError:
                # FFmpeg unavailable — return a minimal error manifest
                return "#EXTM3U\n#EXT-X-VERSION:3\n# Stream unavailable\n"

        manifest_path = self._manifest_path(feed_id)
        if manifest_path.exists():
            return manifest_path.read_text()

        # Manifest not yet written (FFmpeg still starting)
        return "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _manifest_path(self, feed_id: str) -> Path:
        return self.base_dir / feed_id / "live.m3u8"

    def _cleanup_process(self, feed_id: str) -> None:
        proc = self._processes.pop(feed_id, None)
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


# Singleton instance
_hls_service: Optional[HLSService] = None


def get_hls_service() -> HLSService:
    """Return the global HLS service singleton."""
    global _hls_service
    if _hls_service is None:
        _hls_service = HLSService()
    return _hls_service
