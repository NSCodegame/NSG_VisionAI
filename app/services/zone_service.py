"""Security Zone management service"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.security_zone import SecurityZone, ThreatLevel, ZoneType
from app.models.video_feed import VideoFeed
from app.repositories.alert import AlertRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.security_zone import SecurityZoneRepository


class ZoneService:
    """Service for security zone management operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.zone_repo = SecurityZoneRepository(session)
        self.alert_repo = AlertRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def _validate_polygon(self, coordinates: Dict[str, Any]) -> bool:
        """
        Validate polygon coordinates (GeoJSON format).

        Expected format:
        {
            "type": "Polygon",
            "coordinates": [
                [
                    {"lat": 28.6139, "lng": 77.2090},
                    {"lat": 28.6140, "lng": 77.2091},
                    {"lat": 28.6141, "lng": 77.2089},
                    {"lat": 28.6139, "lng": 77.2090}  # First and last must match
                ]
            ]
        }

        Args:
            coordinates: Polygon coordinates dictionary

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(coordinates, dict):
            return False

        if coordinates.get("type") != "Polygon":
            return False

        coords = coordinates.get("coordinates")
        if not isinstance(coords, list) or len(coords) == 0:
            return False

        # Check first ring (exterior boundary)
        ring = coords[0]
        if not isinstance(ring, list) or len(ring) < 4:  # At least 3 points + closing point
            return False

        # Validate each point has lat and lng
        for point in ring:
            if not isinstance(point, dict):
                return False
            if "lat" not in point or "lng" not in point:
                return False
            if not isinstance(point["lat"], (int, float)) or not isinstance(
                point["lng"], (int, float)
            ):
                return False

        # Validate first and last points are identical (closed polygon)
        first_point = ring[0]
        last_point = ring[-1]
        if first_point["lat"] != last_point["lat"] or first_point["lng"] != last_point["lng"]:
            return False

        return True

    async def create_zone(
        self,
        name: str,
        zone_type: ZoneType,
        polygon_coordinates: Dict[str, Any],
        threat_level: ThreatLevel = ThreatLevel.GREEN,
        created_by: Optional[UUID] = None,
        ip_address: Optional[str] = None,
    ) -> SecurityZone:
        """
        Create new security zone.

        Args:
            name: Zone name
            zone_type: Zone type (PERIMETER, RESTRICTED, PUBLIC, INNER_CORDON)
            polygon_coordinates: GeoJSON polygon coordinates
            threat_level: Initial threat level (default: GREEN)
            created_by: User ID creating the zone
            ip_address: Client IP address

        Returns:
            Created SecurityZone

        Raises:
            ValueError: If validation fails
        """
        # Validate polygon coordinates
        if not self._validate_polygon(polygon_coordinates):
            raise ValueError(
                "Invalid polygon coordinates. Must be valid GeoJSON polygon with at least 3 points, "
                "and first/last points must be identical."
            )

        # Create zone record
        zone = await self.zone_repo.create(
            name=name,
            zone_type=zone_type.value,
            polygon_coordinates=polygon_coordinates,
            threat_level=threat_level.value,
        )

        # Create audit log entry
        if created_by:
            await self.audit_repo.create(
                user_id=created_by,
                action="ZONE_CREATED",
                resource_type="SECURITY_ZONE",
                resource_id=zone.id,
                ip_address=ip_address,
                details={
                    "name": name,
                    "zone_type": zone_type.value,
                    "threat_level": threat_level.value,
                },
            )

        await self.session.commit()

        return zone

    async def update_zone(
        self,
        zone_id: UUID,
        name: Optional[str] = None,
        zone_type: Optional[ZoneType] = None,
        polygon_coordinates: Optional[Dict[str, Any]] = None,
        updated_by: Optional[UUID] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[SecurityZone]:
        """
        Update zone details.

        Args:
            zone_id: Zone UUID
            name: New zone name
            zone_type: New zone type
            polygon_coordinates: New polygon coordinates
            updated_by: User ID performing update
            ip_address: Client IP address

        Returns:
            Updated SecurityZone or None if not found

        Raises:
            ValueError: If validation fails
        """
        zone = await self.zone_repo.get(zone_id)
        if zone is None:
            return None

        # Build update dict
        update_data = {}
        details = {}

        if name is not None:
            update_data["name"] = name
            details["name"] = {"old": zone.name, "new": name}

        if zone_type is not None:
            update_data["zone_type"] = zone_type.value
            details["zone_type"] = {"old": zone.zone_type, "new": zone_type.value}

        if polygon_coordinates is not None:
            # Validate polygon if changed
            if not self._validate_polygon(polygon_coordinates):
                raise ValueError(
                    "Invalid polygon coordinates. Must be valid GeoJSON polygon with at least 3 points, "
                    "and first/last points must be identical."
                )
            update_data["polygon_coordinates"] = polygon_coordinates
            details["polygon_coordinates"] = "updated"

        # Update zone
        if update_data:
            zone = await self.zone_repo.update(zone_id, **update_data)

            # Create audit log entry
            if updated_by:
                await self.audit_repo.create(
                    user_id=updated_by,
                    action="ZONE_UPDATED",
                    resource_type="SECURITY_ZONE",
                    resource_id=zone_id,
                    ip_address=ip_address,
                    details=details,
                )

            await self.session.commit()

        return zone

    async def update_threat_level(
        self,
        zone_id: UUID,
        threat_level: ThreatLevel,
        confirmation: bool = False,
        updated_by: Optional[UUID] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[Optional[SecurityZone], int]:
        """
        Update zone threat level and recalculate alert priorities.

        Args:
            zone_id: Zone UUID
            threat_level: New threat level
            confirmation: Required for CRITICAL level
            updated_by: User ID performing update
            ip_address: Client IP address

        Returns:
            Tuple of (Updated SecurityZone or None, affected alert count)

        Raises:
            ValueError: If CRITICAL level without confirmation
        """
        zone = await self.zone_repo.get(zone_id)
        if zone is None:
            return None, 0

        # Require confirmation for CRITICAL level
        if threat_level == ThreatLevel.CRITICAL and not confirmation:
            raise ValueError(
                "Confirmation required to set threat level to CRITICAL. "
                "Set confirmation=true to proceed."
            )

        old_threat_level = zone.threat_level

        # Update zone threat level
        zone = await self.zone_repo.update(zone_id, threat_level=threat_level.value)

        # Recalculate alert priorities for all active alerts in this zone
        affected_count = 0
        if old_threat_level != threat_level.value:
            # Get all active alerts in this zone
            active_alerts = await self.alert_repo.get_multi(
                filters=[
                    Alert.zone_id == zone_id,
                    Alert.status == AlertStatus.ACTIVE.value,
                ],
                limit=10000,  # Get all active alerts
            )

            # Recalculate priority for each alert
            for alert in active_alerts:
                confidence = float(alert.confidence_score) if alert.confidence_score else 0.0
                new_priority = Alert.calculate_priority(
                    alert.alert_type, threat_level.value, confidence
                )

                if new_priority != alert.priority:
                    await self.alert_repo.update(alert.id, priority=new_priority)
                    affected_count += 1

        # Create audit log entry
        if updated_by:
            await self.audit_repo.create(
                user_id=updated_by,
                action="ZONE_THREAT_LEVEL_UPDATED",
                resource_type="SECURITY_ZONE",
                resource_id=zone_id,
                ip_address=ip_address,
                details={
                    "name": zone.name,
                    "old_threat_level": old_threat_level,
                    "new_threat_level": threat_level.value,
                    "affected_alerts": affected_count,
                    "confirmation_provided": confirmation,
                },
            )

        await self.session.commit()

        return zone, affected_count

    async def delete_zone(
        self,
        zone_id: UUID,
        deleted_by: Optional[UUID] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[SecurityZone]:
        """
        Delete zone (check for dependencies first).

        Args:
            zone_id: Zone UUID
            deleted_by: User ID performing deletion
            ip_address: Client IP address

        Returns:
            Deleted SecurityZone or None if not found

        Raises:
            ValueError: If zone has active feeds
        """
        zone = await self.zone_repo.get(zone_id)
        if zone is None:
            return None

        # Check if any feeds are using this zone
        result = await self.session.execute(
            select(VideoFeed).where(VideoFeed.zone_id == zone_id).limit(1)
        )
        feed = result.scalar_one_or_none()

        if feed is not None:
            raise ValueError(
                f"Cannot delete zone '{zone.name}'. "
                f"It is currently assigned to one or more video feeds. "
                f"Please reassign or delete the feeds first."
            )

        # Delete zone
        await self.zone_repo.delete(zone_id)

        # Create audit log entry
        if deleted_by:
            await self.audit_repo.create(
                user_id=deleted_by,
                action="ZONE_DELETED",
                resource_type="SECURITY_ZONE",
                resource_id=zone_id,
                ip_address=ip_address,
                details={
                    "name": zone.name,
                    "zone_type": zone.zone_type,
                    "threat_level": zone.threat_level,
                },
            )

        await self.session.commit()

        return zone

    async def get_zones(
        self,
        zone_type: Optional[ZoneType] = None,
        threat_level: Optional[ThreatLevel] = None,
    ) -> List[SecurityZone]:
        """
        Get all zones with optional filtering.

        Args:
            zone_type: Filter by zone type
            threat_level: Filter by threat level

        Returns:
            List of SecurityZone
        """
        filters = []

        if zone_type is not None:
            filters.append(SecurityZone.zone_type == zone_type.value)

        if threat_level is not None:
            filters.append(SecurityZone.threat_level == threat_level.value)

        return await self.zone_repo.get_multi(
            filters=filters if filters else None,
            limit=10000,  # No pagination needed (zones are limited)
        )
