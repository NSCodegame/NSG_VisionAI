"""
Watchlist Service — Phase 10, Task 10.2

Manages the lifecycle of watchlist entries, including biometric enrollment,
image archival, and approval workflows.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import cv2
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.detection.face_worker import get_face_worker
from app.models.watchlist_entry import WatchlistEntry, WatchlistStatus
from app.repositories.watchlist import WatchlistRepository
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)

class WatchlistService:
    """
    Business logic for biometric enrollment and watchlist management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.watchlist_repo = WatchlistRepository(session)

    async def create_watchlist_entry(
        self,
        added_by: UUID,
        entry_data: dict,
        image_bytes_list: List[bytes]
    ) -> WatchlistEntry:
        """
        Create a new watchlist entry with face embeddings.
        
        Args:
            added_by: UUID of the user adding the entry
            entry_data: Basic info (name, threat_category, etc.)
            image_bytes_list: List of raw JPEG images for enrollment
            
        Returns:
            The created WatchlistEntry.
        """
        face_worker = get_face_worker()
        embeddings = []
        storage_paths = []

        # 1. Process images and extract embeddings
        for i, img_bytes in enumerate(image_bytes_list):
            try:
                # Decode image
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # Detect and embed
                # We expect at least one face per enrollment image
                results = face_worker.detect_and_embed(frame)
                if results:
                    # Use the first/best face detected in each image
                    embeddings.append(results[0]["embedding"])
                    
                    # Upload original enrollment image to MinIO
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    object_name = f"watchlist/enrollment/{ts}_{i}.jpg"
                    success = minio_client.upload_bytes(img_bytes, object_name, "image/jpeg")
                    if success:
                        storage_paths.append(object_name)

            except Exception as e:
                logger.error("Error processing enrollment image %d: %s", i, e)
                continue

        if not embeddings:
            raise ValueError("No valid faces detected in the provided images.")

        # 2. Average embeddings if multiple images provided (centroid of face cluster)
        # 512-dim embedding
        final_embedding = np.mean(embeddings, axis=0).tolist()

        # 3. Persist to Database
        entry = await self.watchlist_repo.create(
            name=entry_data.get("name"),
            alias=entry_data.get("alias"),
            threat_category=entry_data.get("threat_category"),
            description=entry_data.get("description"),
            nationality=entry_data.get("nationality"),
            source_agency=entry_data.get("source_agency"),
            face_images={"paths": storage_paths},
            face_embedding=final_embedding,
            status=WatchlistStatus.PENDING_APPROVAL.value,
            added_by=added_by,
            added_at=datetime.now(timezone.utc)
        )
        
        await self.session.commit()
        return entry

    async def approve_entry(self, entry_id: UUID, approved_by: UUID) -> Optional[WatchlistEntry]:
        """Approve a watchlist entry for active monitoring."""
        entry = await self.watchlist_repo.approve(entry_id, approved_by)
        await self.session.commit()
        return entry

    async def get_active_watchlist(self) -> List[WatchlistEntry]:
        """Retrieve all active targets."""
        return await self.watchlist_repo.get_active_entries()
