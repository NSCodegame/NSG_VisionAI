"""Watchlist repository"""
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlist_entry import ThreatCategory, WatchlistEntry, WatchlistStatus
from app.repositories.base import BaseRepository


class WatchlistRepository(BaseRepository[WatchlistEntry]):
    """Repository for WatchlistEntry model with pgvector similarity search"""

    def __init__(self, session: AsyncSession):
        super().__init__(WatchlistEntry, session)

    async def search_by_embedding(
        self,
        embedding: List[float],
        threshold: float = 0.85,
        limit: int = 10,
    ) -> List[tuple[WatchlistEntry, float]]:
        """
        Search watchlist by face embedding similarity using pgvector.

        Args:
            embedding: 512-dimensional face embedding
            threshold: Similarity threshold (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of (WatchlistEntry, similarity_score) tuples
        """
        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Use pgvector cosine similarity operator (<=>)
        # Lower distance = higher similarity
        # Convert to similarity: 1 - distance
        query = text(
            """
            SELECT *, 1 - (face_embedding <=> :embedding::vector) as similarity
            FROM watchlist_entries
            WHERE status = 'ACTIVE'
            AND face_embedding IS NOT NULL
            AND 1 - (face_embedding <=> :embedding::vector) >= :threshold
            ORDER BY face_embedding <=> :embedding::vector
            LIMIT :limit
            """
        )

        result = await self.session.execute(
            query,
            {"embedding": embedding_str, "threshold": threshold, "limit": limit},
        )

        matches = []
        for row in result:
            entry = await self.get(row.id)
            if entry:
                matches.append((entry, float(row.similarity)))

        return matches

    async def get_active_entries(self, skip: int = 0, limit: int = 100) -> List[WatchlistEntry]:
        """Get active watchlist entries"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[WatchlistEntry.status == WatchlistStatus.ACTIVE.value],
        )

    async def get_pending_approval(
        self, skip: int = 0, limit: int = 100
    ) -> List[WatchlistEntry]:
        """Get entries pending approval"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[WatchlistEntry.status == WatchlistStatus.PENDING_APPROVAL.value],
        )

    async def approve(self, entry_id: UUID, approved_by: UUID) -> Optional[WatchlistEntry]:
        """Approve watchlist entry"""
        from datetime import datetime

        return await self.update(
            entry_id,
            status=WatchlistStatus.ACTIVE.value,
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
        )

    async def deactivate(self, entry_id: UUID) -> Optional[WatchlistEntry]:
        """Deactivate watchlist entry"""
        return await self.update(entry_id, status=WatchlistStatus.DEACTIVATED.value)
