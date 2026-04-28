"""Tracked Person repository"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracked_person import OperatorLabel, TrackedPerson
from app.repositories.base import BaseRepository


class TrackedPersonRepository(BaseRepository[TrackedPerson]):
    """Repository for TrackedPerson model"""

    def __init__(self, session: AsyncSession):
        super().__init__(TrackedPerson, session)

    async def get_by_track_id(self, track_id: str) -> Optional[TrackedPerson]:
        """Get tracked person by ByteTrack ID"""
        result = await self.session.execute(
            select(TrackedPerson).where(TrackedPerson.track_id == track_id)
        )
        return result.scalar_one_or_none()

    async def get_active_persons(
        self, minutes: int = 30, skip: int = 0, limit: int = 100
    ) -> List[TrackedPerson]:
        """Get persons seen within last N minutes"""
        from datetime import datetime, timedelta

        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[TrackedPerson.last_seen_at >= cutoff_time],
            order_by=TrackedPerson.last_seen_at.desc(),
        )

    async def update_trajectory(
        self, person_id: UUID, trajectory_point: Dict[str, Any]
    ) -> Optional[TrackedPerson]:
        """
        Append new point to trajectory.

        Args:
            person_id: Tracked person UUID
            trajectory_point: New trajectory point
                {
                    "feed_id": "uuid",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "position": {"x": 0.5, "y": 0.3}
                }

        Returns:
            Updated tracked person or None
        """
        person = await self.get(person_id)
        if person is None:
            return None

        # Initialize trajectory if None
        if person.trajectory is None:
            person.trajectory = {"points": []}

        # Append new point
        person.trajectory["points"].append(trajectory_point)

        await self.session.flush()
        await self.session.refresh(person)
        return person

    async def update_label(
        self, person_id: UUID, label: OperatorLabel
    ) -> Optional[TrackedPerson]:
        """Update operator label"""
        return await self.update(person_id, operator_label=label.value)

    async def get_by_watchlist_match(
        self, skip: int = 0, limit: int = 100
    ) -> List[TrackedPerson]:
        """Get persons with watchlist matches"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[TrackedPerson.watchlist_match == True],
            order_by=TrackedPerson.last_seen_at.desc(),
        )

    async def find_similar_persons(
        self, embedding: List[float], threshold: float = 0.15, limit: int = 5
    ) -> List[TrackedPerson]:
        """
        Find candidates with similar visual features using cosine distance.
        Distance < 0.15 typically correlates to high visual similarity (>85%).
        """
        result = await self.session.execute(
            select(TrackedPerson)
            .where(TrackedPerson.reid_embedding.cosine_distance(embedding) < threshold)
            .order_by(TrackedPerson.reid_embedding.cosine_distance(embedding).asc())
            .limit(limit)
        )
        return result.scalars().all()
