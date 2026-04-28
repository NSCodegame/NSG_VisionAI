"""
Forensic Search Service — Phase 18, Task 18.1

Provides async archive search capabilities:
- Face similarity search using pgvector
- Object class search with filters
- Zone-based event search
- Person movement timeline reconstruction
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection_event import DetectionEvent, DetectionType
from app.models.report import ForensicJob, ForensicJobStatus, ForensicJobType
from app.models.tracked_person import TrackedPerson
from app.models.watchlist_entry import WatchlistEntry

logger = logging.getLogger(__name__)


class ForensicService:
    """
    Service for forensic archive search operations.
    All searches are async and tracked via ForensicJob records.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    async def create_search_job(
        self,
        job_type: str,
        params: Dict[str, Any],
        created_by: UUID,
    ) -> ForensicJob:
        """
        Create an async forensic search job.

        Args:
            job_type: One of ForensicJobType values
            params: Search parameters dict
            created_by: UUID of requesting user

        Returns:
            Created ForensicJob instance
        """
        job = ForensicJob(
            id=uuid.uuid4(),
            job_type=job_type,
            search_params=params,
            status=ForensicJobStatus.PENDING.value,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        logger.info("Created forensic job %s (type=%s)", job.id, job_type)
        return job

    async def get_job_status(self, job_id: UUID) -> Optional[ForensicJob]:
        """Get forensic job by ID."""
        result = await self.session.execute(
            select(ForensicJob).where(ForensicJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def _update_job(
        self,
        job_id: UUID,
        status: str,
        results: Optional[List[Any]] = None,
        result_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job status and results."""
        job = await self.get_job_status(job_id)
        if job is None:
            return

        job.status = status
        if results is not None:
            job.results = results
            job.result_count = len(results)
        if result_count is not None:
            job.result_count = result_count
        if error_message is not None:
            job.error_message = error_message
        if status in (ForensicJobStatus.COMPLETED.value, ForensicJobStatus.FAILED.value):
            job.completed_at = datetime.now(timezone.utc)

        await self.session.commit()

    # -------------------------------------------------------------------------
    # Face Search
    # -------------------------------------------------------------------------

    async def face_search(
        self,
        job_id: UUID,
        embedding: Optional[List[float]] = None,
        watchlist_entry_id: Optional[UUID] = None,
        similarity_threshold: float = 0.85,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        feed_ids: Optional[List[UUID]] = None,
        zone_ids: Optional[List[UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search archive for face matches using pgvector similarity.

        Args:
            job_id: Job ID to update with results
            embedding: 512-dim face embedding vector
            watchlist_entry_id: Alternative: search by watchlist entry
            similarity_threshold: Minimum cosine similarity (0.0-1.0)
            from_dt: Start datetime filter
            to_dt: End datetime filter
            feed_ids: Optional feed scope filter
            zone_ids: Optional zone scope filter

        Returns:
            List of matching detection event dicts
        """
        await _update_job_status(self.session, job_id, ForensicJobStatus.RUNNING.value)

        try:
            # If watchlist_entry_id provided, load its embedding
            if watchlist_entry_id and embedding is None:
                entry_result = await self.session.execute(
                    select(WatchlistEntry).where(WatchlistEntry.id == watchlist_entry_id)
                )
                entry = entry_result.scalar_one_or_none()
                if entry and entry.face_embedding is not None:
                    embedding = entry.face_embedding

            if embedding is None:
                await self._update_job(
                    job_id,
                    ForensicJobStatus.FAILED.value,
                    error_message="No embedding provided for face search",
                )
                return []

            # Build base query for face detection events
            filters = [DetectionEvent.detection_type == DetectionType.FACE.value]

            if from_dt:
                filters.append(DetectionEvent.frame_timestamp >= from_dt)
            if to_dt:
                filters.append(DetectionEvent.frame_timestamp <= to_dt)
            if feed_ids:
                filters.append(DetectionEvent.feed_id.in_(feed_ids))
            if zone_ids:
                filters.append(DetectionEvent.zone_id.in_(zone_ids))

            # Search tracked persons with pgvector similarity
            # Using cosine distance: 1 - cosine_similarity
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

            pgvector_query = f"""
                SELECT tp.id, tp.track_id, tp.face_embedding,
                       1 - (tp.face_embedding <=> '{embedding_str}'::vector) AS similarity
                FROM tracked_persons tp
                WHERE tp.face_embedding IS NOT NULL
                  AND 1 - (tp.face_embedding <=> '{embedding_str}'::vector) >= :threshold
                ORDER BY similarity DESC
                LIMIT 100
            """

            from sqlalchemy import text
            person_result = await self.session.execute(
                text(pgvector_query), {"threshold": similarity_threshold}
            )
            matching_persons = person_result.fetchall()

            if not matching_persons:
                await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=[])
                return []

            # Get detection events for matching persons
            person_ids = [row[0] for row in matching_persons]
            similarity_map = {row[0]: float(row[3]) for row in matching_persons}

            events_result = await self.session.execute(
                select(DetectionEvent)
                .where(
                    and_(
                        DetectionEvent.person_id.in_(person_ids),
                        *filters,
                    )
                )
                .order_by(DetectionEvent.frame_timestamp.desc())
                .limit(500)
            )
            events = events_result.scalars().all()

            results = [
                {
                    "detection_event_id": str(event.id),
                    "feed_id": str(event.feed_id),
                    "person_id": str(event.person_id) if event.person_id else None,
                    "similarity": similarity_map.get(event.person_id, 0.0),
                    "confidence_score": float(event.confidence_score) if event.confidence_score else 0.0,
                    "frame_timestamp": event.frame_timestamp.isoformat(),
                    "bounding_box": event.bounding_box,
                    "thumbnail_path": event.frame_snapshot_path,
                }
                for event in events
            ]

            await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=results)
            return results

        except Exception as e:
            logger.error("Face search failed for job %s: %s", job_id, e)
            await self._update_job(
                job_id, ForensicJobStatus.FAILED.value, error_message=str(e)
            )
            return []

    # -------------------------------------------------------------------------
    # Object Search
    # -------------------------------------------------------------------------

    async def object_search(
        self,
        job_id: UUID,
        object_class: str,
        confidence_threshold: float = 0.75,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        feed_ids: Optional[List[UUID]] = None,
        zone_ids: Optional[List[UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search archive for object detections by class.

        Args:
            job_id: Job ID to update with results
            object_class: Object class to search (e.g., 'weapon', 'vehicle')
            confidence_threshold: Minimum confidence score
            from_dt: Start datetime filter
            to_dt: End datetime filter
            feed_ids: Optional feed scope filter
            zone_ids: Optional zone scope filter

        Returns:
            List of matching detection event dicts
        """
        await _update_job_status(self.session, job_id, ForensicJobStatus.RUNNING.value)

        try:
            filters = [
                DetectionEvent.detection_type == DetectionType.OBJECT.value,
                DetectionEvent.object_class == object_class,
                DetectionEvent.confidence_score >= confidence_threshold,
            ]

            if from_dt:
                filters.append(DetectionEvent.frame_timestamp >= from_dt)
            if to_dt:
                filters.append(DetectionEvent.frame_timestamp <= to_dt)
            if feed_ids:
                filters.append(DetectionEvent.feed_id.in_(feed_ids))
            if zone_ids:
                filters.append(DetectionEvent.zone_id.in_(zone_ids))

            result = await self.session.execute(
                select(DetectionEvent)
                .where(and_(*filters))
                .order_by(DetectionEvent.frame_timestamp.desc())
                .limit(1000)
            )
            events = result.scalars().all()

            results = [
                {
                    "detection_event_id": str(event.id),
                    "feed_id": str(event.feed_id),
                    "object_class": event.object_class,
                    "confidence_score": float(event.confidence_score) if event.confidence_score else 0.0,
                    "frame_timestamp": event.frame_timestamp.isoformat(),
                    "bounding_box": event.bounding_box,
                    "thumbnail_path": event.frame_snapshot_path,
                }
                for event in events
            ]

            await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=results)
            return results

        except Exception as e:
            logger.error("Object search failed for job %s: %s", job_id, e)
            await self._update_job(
                job_id, ForensicJobStatus.FAILED.value, error_message=str(e)
            )
            return []

    # -------------------------------------------------------------------------
    # Zone Search
    # -------------------------------------------------------------------------

    async def zone_search(
        self,
        job_id: UUID,
        zone_id: UUID,
        event_type: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search archive for events in a specific zone.

        Args:
            job_id: Job ID to update with results
            zone_id: Zone UUID to search
            event_type: Optional detection type filter
            from_dt: Start datetime filter
            to_dt: End datetime filter

        Returns:
            List of matching detection event dicts
        """
        await _update_job_status(self.session, job_id, ForensicJobStatus.RUNNING.value)

        try:
            # DetectionEvent doesn't have zone_id directly; filter via feed_id
            # In production, you'd join with video_feeds to filter by zone
            filters = []

            if event_type:
                filters.append(DetectionEvent.detection_type == event_type)
            if from_dt:
                filters.append(DetectionEvent.frame_timestamp >= from_dt)
            if to_dt:
                filters.append(DetectionEvent.frame_timestamp <= to_dt)

            # Filter by feeds in the zone (join approach)
            from sqlalchemy import text as sa_text
            zone_feed_query = sa_text(
                "SELECT id FROM video_feeds WHERE zone_id = :zone_id"
            )
            zone_feeds_result = await self.session.execute(
                zone_feed_query, {"zone_id": str(zone_id)}
            )
            feed_ids_in_zone = [row[0] for row in zone_feeds_result.fetchall()]

            if feed_ids_in_zone:
                filters.append(DetectionEvent.feed_id.in_(feed_ids_in_zone))
            else:
                # No feeds in zone — return empty results
                await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=[])
                return []

            result = await self.session.execute(
                select(DetectionEvent)
                .where(and_(*filters))
                .order_by(DetectionEvent.frame_timestamp.desc())
                .limit(1000)
            )
            events = result.scalars().all()

            results = [
                {
                    "detection_event_id": str(event.id),
                    "feed_id": str(event.feed_id),
                    "detection_type": event.detection_type,
                    "object_class": event.object_class,
                    "confidence_score": float(event.confidence_score) if event.confidence_score else 0.0,
                    "frame_timestamp": event.frame_timestamp.isoformat(),
                    "bounding_box": event.bounding_box,
                }
                for event in events
            ]

            await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=results)
            return results

        except Exception as e:
            logger.error("Zone search failed for job %s: %s", job_id, e)
            await self._update_job(
                job_id, ForensicJobStatus.FAILED.value, error_message=str(e)
            )
            return []

    # -------------------------------------------------------------------------
    # Timeline Search
    # -------------------------------------------------------------------------

    async def timeline_search(
        self,
        job_id: UUID,
        person_id: Optional[UUID] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct person movement timeline across all feeds.

        Args:
            job_id: Job ID to update with results
            person_id: TrackedPerson UUID
            from_dt: Start datetime filter
            to_dt: End datetime filter

        Returns:
            Chronological list of detection events with feed transitions
        """
        await _update_job_status(self.session, job_id, ForensicJobStatus.RUNNING.value)

        try:
            if person_id is None:
                await self._update_job(
                    job_id,
                    ForensicJobStatus.FAILED.value,
                    error_message="person_id is required for timeline search",
                )
                return []

            filters = [DetectionEvent.person_id == person_id]

            if from_dt:
                filters.append(DetectionEvent.frame_timestamp >= from_dt)
            if to_dt:
                filters.append(DetectionEvent.frame_timestamp <= to_dt)

            result = await self.session.execute(
                select(DetectionEvent)
                .where(and_(*filters))
                .order_by(DetectionEvent.frame_timestamp.asc())
                .limit(2000)
            )
            events = result.scalars().all()

            # Build timeline with feed transitions
            timeline = []
            prev_feed_id = None

            for event in events:
                entry = {
                    "detection_event_id": str(event.id),
                    "feed_id": str(event.feed_id),
                    "detection_type": event.detection_type,
                    "confidence_score": float(event.confidence_score) if event.confidence_score else 0.0,
                    "frame_timestamp": event.frame_timestamp.isoformat(),
                    "bounding_box": event.bounding_box,
                    "thumbnail_path": event.frame_snapshot_path,
                    "feed_transition": prev_feed_id is not None and str(event.feed_id) != str(prev_feed_id),
                }
                timeline.append(entry)
                prev_feed_id = event.feed_id

            await self._update_job(job_id, ForensicJobStatus.COMPLETED.value, results=timeline)
            return timeline

        except Exception as e:
            logger.error("Timeline search failed for job %s: %s", job_id, e)
            await self._update_job(
                job_id, ForensicJobStatus.FAILED.value, error_message=str(e)
            )
            return []


async def _update_job_status(session: AsyncSession, job_id: UUID, status: str) -> None:
    """Helper to update job status."""
    result = await session.execute(
        select(ForensicJob).where(ForensicJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job:
        job.status = status
        await session.commit()
