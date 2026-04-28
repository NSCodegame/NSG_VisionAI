"""Video Feed management service"""
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import cv2
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.video_feed import FeedStatus, FeedType, VideoFeed
from app.repositories.audit_log import AuditLogRepository
from app.repositories.video_feed import VideoFeedRepository
from app.utils.encryption import decrypt_rtsp_url, encrypt_rtsp_url


class FeedService:
    """Service for video feed management operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feed_repo = VideoFeedRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def _validate_rtsp_url(self, url: str) -> bool:
        """
        Validate RTSP URL format.

        Args:
            url: RTSP URL to validate

        Returns:
            True if valid, False otherwise
        """
        # RTSP URL pattern: rtsp://[username:password@]host[:port]/path
        pattern = r"^rtsp://(?:[^:@]+(?::[^@]+)?@)?[^:/]+(?::\d+)?(?:/.*)?$"
        return bool(re.match(pattern, url, re.IGNORECASE))

    async def create_feed(
        self,
        name: str,
        feed_type: FeedType,
        rtsp_url: str,
        zone_id: Optional[UUID],
        location_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        ai_enabled: bool = True,
        created_by: UUID = None,
        ip_address: Optional[str] = None,
    ) -> VideoFeed:
        """
        Create new video feed with encrypted RTSP URL.

        Args:
            name: Feed name/identifier
            feed_type: Feed type (FIXED_CAMERA, DRONE, BODY_CAM, LEGACY_CCTV)
            rtsp_url: Plain RTSP URL
            zone_id: Security zone ID (must exist)
            location_name: Human-readable location name
            latitude: GPS latitude
            longitude: GPS longitude
            ai_enabled: Enable AI processing
            created_by: User ID creating the feed
            ip_address: Client IP address

        Returns:
            Created VideoFeed

        Raises:
            ValueError: If validation fails
        """
        # Validate RTSP URL format
        if not self._validate_rtsp_url(rtsp_url):
            raise ValueError(f"Invalid RTSP URL format: {rtsp_url}")

        # Validate zone exists if provided
        if zone_id is not None:
            # Zone validation will be handled by foreign key constraint
            pass

        # Encrypt RTSP URL before storage
        encrypted_url = encrypt_rtsp_url(rtsp_url, settings.encryption_master_key)

        # Create feed record
        feed = await self.feed_repo.create(
            name=name,
            feed_type=feed_type.value,
            rtsp_url_encrypted=encrypted_url,
            zone_id=zone_id,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            status=FeedStatus.OFFLINE.value,
            ai_enabled=ai_enabled,
        )

        # Create audit log entry
        if created_by:
            await self.audit_repo.create(
                user_id=created_by,
                action="FEED_CREATED",
                resource_type="VIDEO_FEED",
                resource_id=feed.id,
                ip_address=ip_address,
                details={
                    "name": name,
                    "feed_type": feed_type.value,
                    "zone_id": str(zone_id) if zone_id else None,
                    "location_name": location_name,
                    "ai_enabled": ai_enabled,
                },
            )

        await self.session.commit()

        return feed

    async def update_feed(
        self,
        feed_id: UUID,
        name: Optional[str] = None,
        rtsp_url: Optional[str] = None,
        zone_id: Optional[UUID] = None,
        location_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        updated_by: UUID = None,
        ip_address: Optional[str] = None,
    ) -> Optional[VideoFeed]:
        """
        Update feed details.

        Args:
            feed_id: Feed UUID
            name: New feed name
            rtsp_url: New RTSP URL (will be re-encrypted)
            zone_id: New zone ID
            location_name: New location name
            latitude: New latitude
            longitude: New longitude
            updated_by: User ID performing update
            ip_address: Client IP address

        Returns:
            Updated VideoFeed or None if not found

        Raises:
            ValueError: If validation fails
        """
        feed = await self.feed_repo.get(feed_id)
        if feed is None:
            return None

        # Build update dict
        update_data = {}
        details = {}

        if name is not None:
            update_data["name"] = name
            details["name"] = {"old": feed.name, "new": name}

        if rtsp_url is not None:
            # Validate and re-encrypt RTSP URL
            if not self._validate_rtsp_url(rtsp_url):
                raise ValueError(f"Invalid RTSP URL format: {rtsp_url}")
            encrypted_url = encrypt_rtsp_url(rtsp_url, settings.encryption_master_key)
            update_data["rtsp_url_encrypted"] = encrypted_url
            details["rtsp_url"] = "updated"

        if zone_id is not None:
            update_data["zone_id"] = zone_id
            details["zone_id"] = {"old": str(feed.zone_id) if feed.zone_id else None, "new": str(zone_id)}

        if location_name is not None:
            update_data["location_name"] = location_name
            details["location_name"] = {"old": feed.location_name, "new": location_name}

        if latitude is not None:
            update_data["latitude"] = latitude
            details["latitude"] = {"old": float(feed.latitude) if feed.latitude else None, "new": latitude}

        if longitude is not None:
            update_data["longitude"] = longitude
            details["longitude"] = {"old": float(feed.longitude) if feed.longitude else None, "new": longitude}

        # Update feed
        if update_data:
            feed = await self.feed_repo.update(feed_id, **update_data)

            # Create audit log entry
            if updated_by:
                await self.audit_repo.create(
                    user_id=updated_by,
                    action="FEED_UPDATED",
                    resource_type="VIDEO_FEED",
                    resource_id=feed_id,
                    ip_address=ip_address,
                    details=details,
                )

            await self.session.commit()

        return feed

    async def delete_feed(
        self,
        feed_id: UUID,
        deleted_by: UUID = None,
        ip_address: Optional[str] = None,
    ) -> Optional[VideoFeed]:
        """
        Soft delete feed (set status to MAINTENANCE).

        Args:
            feed_id: Feed UUID
            deleted_by: User ID performing deletion
            ip_address: Client IP address

        Returns:
            Updated VideoFeed or None if not found
        """
        feed = await self.feed_repo.get(feed_id)
        if feed is None:
            return None

        # Soft delete by setting status to MAINTENANCE and disabling AI
        feed = await self.feed_repo.update(
            feed_id,
            status=FeedStatus.MAINTENANCE.value,
            ai_enabled=False,
        )

        # Create audit log entry
        if deleted_by:
            await self.audit_repo.create(
                user_id=deleted_by,
                action="FEED_DELETED",
                resource_type="VIDEO_FEED",
                resource_id=feed_id,
                ip_address=ip_address,
                details={
                    "name": feed.name,
                    "feed_type": feed.feed_type,
                },
            )

        await self.session.commit()

        return feed

    async def toggle_ai_processing(
        self,
        feed_id: UUID,
        toggled_by: UUID = None,
        ip_address: Optional[str] = None,
    ) -> Optional[VideoFeed]:
        """
        Toggle AI processing flag for feed.

        Args:
            feed_id: Feed UUID
            toggled_by: User ID performing toggle
            ip_address: Client IP address

        Returns:
            Updated VideoFeed or None if not found
        """
        feed = await self.feed_repo.toggle_ai_processing(feed_id)

        if feed:
            # Create audit log entry
            if toggled_by:
                await self.audit_repo.create(
                    user_id=toggled_by,
                    action="FEED_AI_TOGGLED",
                    resource_type="VIDEO_FEED",
                    resource_id=feed_id,
                    ip_address=ip_address,
                    details={
                        "name": feed.name,
                        "ai_enabled": feed.ai_enabled,
                    },
                )

            await self.session.commit()

        return feed

    async def test_connection(
        self,
        rtsp_url: str,
        timeout: int = 10,
    ) -> Dict[str, any]:
        """
        Test RTSP connection using OpenCV VideoCapture.

        Args:
            rtsp_url: Plain RTSP URL to test
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            Dictionary with connection result:
            {
                "success": bool,
                "message": str,
                "metadata": {
                    "resolution": str,  # e.g., "1920x1080"
                    "fps": float,
                    "codec": str,
                } or None
            }
        """
        result = {
            "success": False,
            "message": "",
            "metadata": None,
        }

        try:
            # Create VideoCapture with timeout
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

            # Set timeout (in milliseconds)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)

            # Try to open stream with timeout
            async def open_stream():
                return cap.isOpened()

            # Run with timeout
            is_opened = await asyncio.wait_for(
                asyncio.to_thread(open_stream),
                timeout=timeout
            )

            if is_opened:
                # Get stream metadata
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

                # Convert fourcc to codec string
                codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

                result["success"] = True
                result["message"] = "Connection successful"
                result["metadata"] = {
                    "resolution": f"{width}x{height}",
                    "fps": fps if fps > 0 else None,
                    "codec": codec.strip() if codec.strip() else None,
                }
            else:
                result["message"] = "Failed to open RTSP stream"

            # Release capture
            cap.release()

        except asyncio.TimeoutError:
            result["message"] = f"Connection timeout after {timeout} seconds"
        except Exception as e:
            result["message"] = f"Connection error: {str(e)}"

        return result

    async def get_feeds(
        self,
        feed_type: Optional[FeedType] = None,
        zone_id: Optional[UUID] = None,
        status: Optional[FeedStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[VideoFeed]:
        """
        Get feeds with filtering and pagination.

        Args:
            feed_type: Filter by feed type
            zone_id: Filter by zone ID
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of VideoFeed
        """
        filters = []

        if feed_type is not None:
            filters.append(VideoFeed.feed_type == feed_type.value)

        if zone_id is not None:
            filters.append(VideoFeed.zone_id == zone_id)

        if status is not None:
            filters.append(VideoFeed.status == status.value)

        return await self.feed_repo.get_multi(
            skip=skip,
            limit=limit,
            filters=filters if filters else None,
        )
