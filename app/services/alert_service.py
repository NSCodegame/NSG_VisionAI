"""
Alert Service — Phase 13, Task 13.1

Logic engine for alert generation, deduplication, and prioritization.
Integrates ML detection events with security protocols.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.websocket import manager
from app.models.alert import Alert, AlertPriority, AlertStatus, AlertType
from app.models.detection_event import DetectionType
from app.repositories.alert import AlertRepository

logger = logging.getLogger(__name__)

class AlertService:
    """
    Service for processing detection events and managing alert lifecycle.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_repo = AlertRepository(session)

    def _map_detection_to_alert_type(self, detection_type: DetectionType, object_class: Optional[str]) -> AlertType:
        """Map ML detection type to Alert model type."""
        if detection_type == DetectionType.FACE:
            return AlertType.WATCHLIST_MATCH
        if detection_type == DetectionType.ANOMALY:
            return AlertType.LOITERING # Default anomaly type, can be refined
        
        if detection_type == DetectionType.OBJECT:
            if object_class in ["weapon", "pistol", "rifle"]:
                return AlertType.WEAPON_DETECTED
            if object_class in ["abandoned_bag", "suitcase"]:
                return AlertType.UNATTENDED_OBJECT
            if object_class == "vehicle":
                return AlertType.VEHICLE_THREAT
                
        return AlertType.UNATTENDED_OBJECT # Fallback

    async def process_detection(
        self,
        event_id: UUID,
        feed_id: UUID,
        detection_type: DetectionType,
        confidence: float,
        object_class: Optional[str] = None,
        zone_id: Optional[UUID] = None,
        zone_threat_level: str = "GREEN"
    ) -> Optional[Alert]:
        """
        Process a detection event: Deduplicate -> Prioritize -> Create Alert.
        """
        alert_type = self._map_detection_to_alert_type(detection_type, object_class)
        
        # 1. Deduplication (Window: 30s)
        # Check if an active alert of same type exists for this feed
        existing = await self.alert_repo.find_duplicate(
            feed_id=feed_id,
            alert_type=alert_type,
            window_seconds=30
        )
        
        if existing:
            # Increment occurrence count instead of creating new alert
            logger.info("Deduplicating alert for feed %s, type %s", feed_id, alert_type)
            alert = await self.alert_repo.increment_occurrence(existing.id)
            await self.session.commit()
            return alert

        # 2. Priority Calculation
        priority = Alert.calculate_priority(
            alert_type=alert_type.value,
            zone_threat_level=zone_threat_level,
            confidence_score=confidence
        )

        # 3. Create Alert
        alert = await self.alert_repo.create(
            detection_event_id=event_id,
            alert_type=alert_type.value,
            priority=priority,
            status=AlertStatus.ACTIVE.value,
            feed_id=feed_id,
            zone_id=zone_id,
            confidence_score=confidence,
            triggered_at=datetime.now(timezone.utc),
            occurrence_count=1
        )
        
        await self.session.commit()
        logger.info("New ALERT generated: ID %s, Type %s, Priority %s", 
                    alert.id, alert_type, priority)
        
        # 4. Broadcast to WebSockets
        if priority in ["P1_CRITICAL", "P2_HIGH"]:
            await manager.broadcast({
                "type": "NEW_ALERT",
                "alert": {
                    "id": str(alert.id),
                    "type": alert.alert_type,
                    "priority": alert.priority,
                    "feed_id": str(alert.feed_id),
                    "confidence": float(alert.confidence_score),
                    "triggered_at": alert.triggered_at.isoformat()
                }
            })
        
        return alert
