"""Security Zone repository"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_zone import SecurityZone, ThreatLevel, ZoneType
from app.repositories.base import BaseRepository


class SecurityZoneRepository(BaseRepository[SecurityZone]):
    """Repository for SecurityZone model"""

    def __init__(self, session: AsyncSession):
        super().__init__(SecurityZone, session)

    async def get_by_threat_level(
        self, threat_level: ThreatLevel, skip: int = 0, limit: int = 100
    ) -> List[SecurityZone]:
        """Get zones by threat level"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[SecurityZone.threat_level == threat_level.value],
        )

    async def get_by_zone_type(
        self, zone_type: ZoneType, skip: int = 0, limit: int = 100
    ) -> List[SecurityZone]:
        """Get zones by zone type"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[SecurityZone.zone_type == zone_type.value],
        )

    async def get_by_name(self, name: str) -> Optional[SecurityZone]:
        """Get zone by name"""
        result = await self.session.execute(
            select(SecurityZone).where(SecurityZone.name == name)
        )
        return result.scalar_one_or_none()
