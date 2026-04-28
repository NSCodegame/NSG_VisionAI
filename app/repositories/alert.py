"""Alert repository"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertPriority, AlertStatus, AlertType
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """Repository for Alert model"""

    def __init__(self, session: AsyncSession):
        super().__init__(Alert, session)

    async def get_by_priority(
        self, priority: AlertPriority, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """Get alerts by priority"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[Alert.priority == priority.value],
            order_by=Alert.triggered_at.desc(),
        )

    async def get_by_status(
        self, status: AlertStatus, skip: int = 0, limit: int = 100
    ) -> List[Alert]:
        """Get alerts by status"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[Alert.status == status.value],
            order_by=Alert.triggered_at.desc(),
        )

    async def get_by_feed(self, feed_id: UUID, skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get alerts by feed"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[Alert.feed_id == feed_id],
            order_by=Alert.triggered_at.desc(),
        )

    async def get_by_zone(self, zone_id: UUID, skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get alerts by zone"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[Alert.zone_id == zone_id],
            order_by=Alert.triggered_at.desc(),
        )

    async def get_active_alerts(self, skip: int = 0, limit: int = 100) -> List[Alert]:
        """Get all active alerts"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[Alert.status == AlertStatus.ACTIVE.value],
            order_by=[Alert.priority.asc(), Alert.triggered_at.desc()],
        )

    async def acknowledge(self, alert_id: UUID, user_id: UUID) -> Optional[Alert]:
        """Acknowledge an alert"""
        return await self.update(
            alert_id,
            status=AlertStatus.ACKNOWLEDGED.value,
            acknowledged_at=datetime.utcnow(),
            acknowledged_by=user_id,
        )

    async def resolve(
        self, alert_id: UUID, resolution_notes: str
    ) -> Optional[Alert]:
        """Resolve an alert"""
        return await self.update(
            alert_id,
            status=AlertStatus.RESOLVED.value,
            resolved_at=datetime.utcnow(),
            resolution_notes=resolution_notes,
        )

    async def mark_false_positive(
        self, alert_id: UUID, reason: str
    ) -> Optional[Alert]:
        """Mark alert as false positive"""
        return await self.update(
            alert_id,
            status=AlertStatus.FALSE_POSITIVE.value,
            false_positive_reason=reason,
        )

    async def find_duplicate(
        self,
        feed_id: UUID,
        alert_type: AlertType,
        window_seconds: int = 30,
    ) -> Optional[Alert]:
        """
        Find duplicate alert within time window for deduplication.
        
        Args:
            feed_id: Feed UUID
            alert_type: Alert type
            window_seconds: Time window in seconds
            
        Returns:
            Existing alert or None
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        result = await self.session.execute(
            select(Alert)
            .where(
                and_(
                    Alert.feed_id == feed_id,
                    Alert.alert_type == alert_type.value,
                    Alert.triggered_at >= cutoff_time,
                    Alert.status == AlertStatus.ACTIVE.value,
                )
            )
            .order_by(Alert.triggered_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def increment_occurrence(self, alert_id: UUID) -> Optional[Alert]:
        """Increment occurrence count for deduplication"""
        alert = await self.get(alert_id)
        if alert is None:
            return None
        return await self.update(
            alert_id,
            occurrence_count=alert.occurrence_count + 1,
            triggered_at=datetime.utcnow(),
        )


from datetime import timedelta
