"""
IP Camera Configuration Utilities

Provides helpers for:
  - Building RTSP URLs from camera IP / credentials
  - Probing a single camera to detect its working stream path
  - Scanning a subnet to discover cameras that respond on RTSP port 554
  - Generating ONVIF-style device info URLs

Supported camera brands and their default RTSP path patterns are encoded in
BRAND_STREAM_PATHS. The probe logic tries each path in order and returns the
first one that OpenCV can open.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from typing import Optional

import cv2

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Brand-specific RTSP path templates ────────────────────────────────────────

BRAND_STREAM_PATHS: dict[str, list[str]] = {
    "hikvision": [
        "/Streaming/Channels/101",
        "/Streaming/Channels/102",
        "/h264/ch1/main/av_stream",
    ],
    "dahua": [
        "/cam/realmonitor?channel=1&subtype=0",
        "/cam/realmonitor?channel=1&subtype=1",
    ],
    "axis": [
        "/axis-media/media.amp",
        "/axis-media/media.amp?videocodec=h264",
    ],
    "reolink": [
        "/h264Preview_01_main",
        "/h264Preview_01_sub",
    ],
    "amcrest": [
        "/cam/realmonitor?channel=1&subtype=0",
        "/live",
    ],
    "generic": [
        "/stream1",
        "/live",
        "/video1",
        "/live/ch00_0",
        "/h264",
        "/stream",
        "/live/stream",
        "/videoMain",
    ],
}

# Flat list of all paths for generic probing (deduped, generic last)
_ALL_PROBE_PATHS: list[str] = list(
    dict.fromkeys(
        [p for paths in BRAND_STREAM_PATHS.values() for p in paths]
        + settings.ip_camera_stream_paths
    )
)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class IPCameraConfig:
    """Configuration for a single IP camera."""

    ip: str
    port: int = 554
    username: str = "admin"
    password: str = ""
    stream_path: str = "/stream1"
    brand: Optional[str] = None  # e.g. "hikvision", "dahua", "axis"

    @property
    def rtsp_url(self) -> str:
        """Build the full RTSP URL from config fields."""
        if self.username and self.password:
            creds = f"{self.username}:{self.password}@"
        elif self.username:
            creds = f"{self.username}@"
        else:
            creds = ""
        return f"rtsp://{creds}{self.ip}:{self.port}{self.stream_path}"

    @property
    def onvif_url(self) -> str:
        """Build the ONVIF device service URL (HTTP)."""
        onvif_port = settings.ip_camera_onvif_port
        return f"http://{self.ip}:{onvif_port}/onvif/device_service"


@dataclass
class DiscoveredCamera:
    """Result of a camera discovery scan."""

    ip: str
    port: int
    rtsp_url: Optional[str] = None
    stream_path: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    reachable: bool = False
    error: Optional[str] = None


# ── URL builder ───────────────────────────────────────────────────────────────


def build_rtsp_url(
    ip: str,
    port: int = 554,
    username: str = "admin",
    password: str = "",
    stream_path: str = "/stream1",
) -> str:
    """
    Build a complete RTSP URL from individual components.

    Args:
        ip: Camera IP address (e.g. "192.168.1.64")
        port: RTSP port (default 554)
        username: Camera username (default "admin")
        password: Camera password
        stream_path: Stream path (e.g. "/Streaming/Channels/101")

    Returns:
        Full RTSP URL string

    Example:
        >>> build_rtsp_url("192.168.1.64", 554, "admin", "pass123",
        ...                 "/Streaming/Channels/101")
        'rtsp://admin:pass123@192.168.1.64:554/Streaming/Channels/101'
    """
    cfg = IPCameraConfig(
        ip=ip,
        port=port,
        username=username,
        password=password,
        stream_path=stream_path,
    )
    return cfg.rtsp_url


def get_brand_paths(brand: str) -> list[str]:
    """
    Return the known RTSP stream paths for a camera brand.

    Args:
        brand: Brand name (case-insensitive). Falls back to "generic" if unknown.

    Returns:
        List of RTSP path strings to try.
    """
    return BRAND_STREAM_PATHS.get(brand.lower(), BRAND_STREAM_PATHS["generic"])


# ── Camera probing ────────────────────────────────────────────────────────────


async def probe_camera(
    ip: str,
    port: int = 554,
    username: str = "admin",
    password: str = "",
    brand: Optional[str] = None,
    timeout: int = 5,
) -> Optional[DiscoveredCamera]:
    """
    Probe a camera at the given IP to find a working RTSP stream path.

    Tries brand-specific paths first (if brand is given), then falls back to
    the generic list. Returns the first path that OpenCV can open.

    Args:
        ip: Camera IP address
        port: RTSP port (default 554)
        username: Camera username
        password: Camera password
        brand: Optional brand hint to prioritise matching paths
        timeout: Per-path connection timeout in seconds

    Returns:
        DiscoveredCamera with rtsp_url and stream metadata, or None if no
        path worked.
    """
    paths = get_brand_paths(brand) + _ALL_PROBE_PATHS if brand else _ALL_PROBE_PATHS

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_paths = [p for p in paths if not (p in seen or seen.add(p))]

    loop = asyncio.get_event_loop()

    for path in unique_paths:
        url = build_rtsp_url(ip, port, username, password, path)
        logger.debug("Probing %s", url)

        try:
            cap = await asyncio.wait_for(
                loop.run_in_executor(None, _try_open_capture, url),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.debug("Timeout probing %s", url)
            continue
        except Exception as exc:
            logger.debug("Error probing %s: %s", url, exc)
            continue

        if cap is not None:
            # Read stream metadata
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)]).strip()
            cap.release()

            logger.info("Camera at %s:%d responded on path %s", ip, port, path)
            return DiscoveredCamera(
                ip=ip,
                port=port,
                rtsp_url=url,
                stream_path=path,
                resolution=f"{width}x{height}" if width and height else None,
                fps=fps if fps > 0 else None,
                codec=codec or None,
                reachable=True,
            )

    logger.warning("No working stream path found for camera at %s:%d", ip, port)
    return None


def _try_open_capture(url: str) -> Optional[cv2.VideoCapture]:
    """Blocking helper — open a VideoCapture and return it if successful."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if cap.isOpened():
        return cap
    cap.release()
    return None


# ── Port reachability check ───────────────────────────────────────────────────


async def is_rtsp_port_open(ip: str, port: int = 554, timeout: float = 2.0) -> bool:
    """
    Check if the RTSP TCP port is open on the given host.

    Uses a raw socket connect — much faster than opening a full VideoCapture.
    This is used as a pre-filter during subnet scanning.

    Args:
        ip: Host IP address
        port: TCP port to check (default 554)
        timeout: Socket connect timeout in seconds

    Returns:
        True if port is open, False otherwise
    """
    loop = asyncio.get_event_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, _tcp_connect, ip, port),
            timeout=timeout,
        )
        return True
    except (asyncio.TimeoutError, OSError):
        return False


def _tcp_connect(ip: str, port: int) -> None:
    """Blocking TCP connect attempt."""
    with socket.create_connection((ip, port), timeout=2):
        pass


# ── Subnet scanner ────────────────────────────────────────────────────────────


async def scan_subnet_for_cameras(
    subnet: str = "192.168.1.0/24",
    port: int = 554,
    concurrency: int = 50,
    discovery_timeout: Optional[int] = None,
) -> list[DiscoveredCamera]:
    """
    Scan a subnet for hosts with an open RTSP port.

    This is a fast TCP port scan — it does NOT attempt to open streams.
    Use probe_camera() on each result to find working stream paths.

    Args:
        subnet: CIDR subnet string (e.g. "192.168.1.0/24")
        port: RTSP port to check (default 554)
        concurrency: Max simultaneous TCP checks (default 50)
        discovery_timeout: Per-host timeout in seconds (defaults to config value)

    Returns:
        List of DiscoveredCamera for hosts with the port open.
    """
    timeout = discovery_timeout or settings.ip_camera_discovery_timeout
    network = ipaddress.ip_network(subnet, strict=False)
    hosts = list(network.hosts())

    logger.info(
        "Scanning %s (%d hosts) for open port %d …", subnet, len(hosts), port
    )

    semaphore = asyncio.Semaphore(concurrency)
    results: list[DiscoveredCamera] = []

    async def check_host(ip_obj: ipaddress.IPv4Address) -> None:
        ip = str(ip_obj)
        async with semaphore:
            open_ = await is_rtsp_port_open(ip, port, timeout=float(timeout))
            if open_:
                logger.info("Found open RTSP port at %s:%d", ip, port)
                results.append(DiscoveredCamera(ip=ip, port=port, reachable=True))

    await asyncio.gather(*[check_host(h) for h in hosts])
    logger.info("Scan complete — %d camera(s) found", len(results))
    return results
