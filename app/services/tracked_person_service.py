"""
Tracked Person Service — Phase 11, Task 11.2

Manages the lifecycle of tracked individuals, trajectory aggregation,
and cross-camera identification.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.anomaly.lstm_worker import get_anomaly_worker
from app.models.tracked_person import OperatorLabel, TrackedPerson
from app.repositories.tracked_person import TrackedPersonRepository
from app.tasks.anomaly_tasks import detect_anomalies_task

logger = logging.getLogger(__name__)

class TrackedPersonService:
    """
    Business logic for identity tracking and trajectory management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.person_repo = TrackedPersonRepository(session)

    async def update_person_track(
        self,
        feed_id: UUID,
        track_data: Dict,
        timestamp: datetime
    ) -> TrackedPerson:
        """
        Create or update a tracked person based on worker results.
        
        Args:
            feed_id: Source feed UUID
            track_data: Dict with track_id, bounding_box, object_class, confidence
            timestamp: Capture timestamp
            
        Returns:
            The updated TrackedPerson record.
        """
        track_id_str = str(track_data["track_id"])
        
        # 1. Check if track already exists
        person = await self.person_repo.get_by_track_id(track_id_str)
        
        trajectory_point = {
            "feed_id": str(feed_id),
            "timestamp": timestamp.isoformat(),
            "position": {
                "x": track_data["bounding_box"]["x"],
                "y": track_data["bounding_box"]["y"]
            }
        }
        
        if person:
            # Update existing record
            person.last_seen_at = timestamp
            
            # Update Re-ID embedding if we have a new one and record doesn't have one
            if "reid_embedding" in track_data and person.reid_embedding is None:
                person.reid_embedding = track_data["reid_embedding"]

            # Maintain feed_ids_seen
            if person.feed_ids_seen is None:
                person.feed_ids_seen = {"ids": []}
            if str(feed_id) not in person.feed_ids_seen["ids"]:
                person.feed_ids_seen["ids"].append(str(feed_id))
            
            # Trigger Anomaly Detection every N points
            points_count = len(person.trajectory.get("points", []))
            if points_count >= 10 and points_count % 10 == 0:
                detect_anomalies_task.delay(str(person.id))
                
            await self.person_repo.update_trajectory(person.id, trajectory_point)
        else:
            # Create new record
            reid_embedding = track_data.get("reid_embedding")
            parent_id = None
            
            # Cross-camera identity linking
            if reid_embedding:
                # Find visual matches from the last 24 hours (default search window)
                similar_candidates = await self.person_repo.find_similar_persons(reid_embedding, threshold=0.15, limit=1)
                if similar_candidates:
                    parent_id = similar_candidates[0].parent_id or similar_candidates[0].id
                    logger.info("IDENTITY LINKED: Track %s on Feed %s linked to Parent %s", 
                                track_id_str, feed_id, parent_id)
            
            person = await self.person_repo.create(
                track_id=track_id_str,
                first_seen_at=timestamp,
                last_seen_at=timestamp,
                feed_ids_seen={"ids": [str(feed_id)]},
                trajectory={"points": [trajectory_point]},
                operator_label=OperatorLabel.UNKNOWN.value,
                watchlist_match=False,
                reid_embedding=reid_embedding,
                parent_id=parent_id
            )
            
        await self.session.commit()
        return person

    async def list_active_persons(self, limit: int = 100) -> List[TrackedPerson]:
        """List recently seen individuals."""
        return await self.person_repo.get_active_persons(limit=limit)

    async def update_operator_label(
        self, person_id: UUID, label: OperatorLabel, notes: Optional[str] = None
    ) -> Optional[TrackedPerson]:
        """Manually label a tracked individual."""
        person = await self.person_repo.update(person_id, operator_label=label.value, notes=notes)
        await self.session.commit()
        return person
