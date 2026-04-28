"""
TranscodingService — Phase 24, Task 24.1

Manages real-time FFmpeg transcoding of RTSP/SRT streams to web-native HLS.
Uses optimized tactical settings for low-latency delivery.
"""

import logging
import os
import subprocess
import signal
from typing import Dict, Optional
from uuid import UUID
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

class TranscodingService:
    """
    Manages active FFmpeg transcoding processes for live video feeds.
    """

    # Active processes: {feed_id: subprocess.Popen}
    _active_processes: Dict[UUID, subprocess.Popen] = {}

    def __init__(self, stream_dir: Optional[str] = None):
        self.stream_dir = Path(stream_dir or "d:/Project/NSG/streams")
        self.stream_dir.mkdir(parents=True, exist_ok=True)

    async def start_transcoding(self, feed_id: UUID, rtsp_url: str) -> str:
        """
        Start an FFmpeg process for the given feed.
        Returns the path to the .m3u8 playlist file.
        """
        if feed_id in self._active_processes:
            # Check if process is still alive
            if self._active_processes[feed_id].poll() is None:
                return str(self._get_playlist_path(feed_id))
            else:
                self.stop_transcoding(feed_id)

        output_dir = self.stream_dir / str(feed_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = output_dir / "index.m3u8"

        # FFmpeg command for low-latency HLS
        # -preset ultrafast, -tune zerolatency, -hls_time 1 are key for tactical surveillance
        command = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-c:a", "aac",
            "-ar", "44100",
            "-f", "hls",
            "-hls_time", "1",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments+append_list",
            str(playlist_path)
        ]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            self._active_processes[feed_id] = process
            logger.info("Transcoding started for feed %s", feed_id)
            return str(playlist_path)
        except Exception as e:
            logger.error("Failed to start transcoding for feed %s: %s", feed_id, e)
            raise

    def stop_transcoding(self, feed_id: UUID):
        """Stop the FFmpeg process for a feed."""
        if feed_id in self._active_processes:
            process = self._active_processes.pop(feed_id)
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                logger.info("Transcoding stopped for feed %s", feed_id)
            except Exception as e:
                logger.warning("Error stopping FFmpeg for feed %s: %s", feed_id, e)

    def _get_playlist_path(self, feed_id: UUID) -> Path:
        return self.stream_dir / str(feed_id) / "index.m3u8"

def get_transcoding_service() -> TranscodingService:
    """Singleton instance logic."""
    # Note: In a production k8s environment, this might be a separate microservice.
    return TranscodingService()
