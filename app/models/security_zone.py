"""Security Zone Model"""
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import CheckConstraint, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ZoneType(str, PyEnum):
    """Security zone type enumeration"""

    PERIMETER = "PERIMETER"
    RESTRICTED = "RESTRICTED"
    PUBLIC = "PUBLIC"
    INNER_CORDON = "INNER_CORDON"


class ThreatLevel(str, PyEnum):
    """Threat level enumeration"""

    GREEN = "GREEN"  # Low threat
    AMBER = "AMBER"  # Medium threat
    RED = "RED"  # High threat
    CRITICAL = "CRITICAL"  # Critical threat


class SecurityZone(Base, UUIDMixin, TimestampMixin):
    """Security zone model for geographic area management"""

    __tablename__ = "security_zones"

    # Zone identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Zone name")

    # Zone classification
    zone_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Zone type (PERIMETER, RESTRICTED, PUBLIC, INNER_CORDON)",
    )

    # Geographic boundaries
    polygon_coordinates: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Array of {lat, lng} points defining the polygon boundary",
    )

    # Threat assessment
    threat_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Current threat level (GREEN, AMBER, RED, CRITICAL)",
    )

    # Relationships
    feeds: Mapped[list["VideoFeed"]] = relationship("VideoFeed", back_populates="zone", lazy="selectin")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "zone_type IN ('PERIMETER', 'RESTRICTED', 'PUBLIC', 'INNER_CORDON')",
            name="check_zone_type_valid",
        ),
        CheckConstraint(
            "threat_level IN ('GREEN', 'AMBER', 'RED', 'CRITICAL')",
            name="check_threat_level_valid",
        ),
        Index("idx_zones_threat_level", "threat_level"),
    )

    @staticmethod
    def validate_polygon(coordinates: dict[str, Any]) -> bool:
        """
        Validate polygon coordinates structure.

        Expected format:
        {
            "type": "Polygon",
            "coordinates": [
                [
                    {"lat": 28.6139, "lng": 77.2090},
                    {"lat": 28.6140, "lng": 77.2091},
                    ...
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
            if not isinstance(point["lat"], (int, float)) or not isinstance(point["lng"], (int, float)):
                return False

        # Validate first and last points are identical (closed polygon)
        first_point = ring[0]
        last_point = ring[-1]
        if first_point["lat"] != last_point["lat"] or first_point["lng"] != last_point["lng"]:
            return False

        return True

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<SecurityZone(id={self.id}, name='{self.name}', "
            f"zone_type='{self.zone_type}', threat_level='{self.threat_level}')>"
        )
