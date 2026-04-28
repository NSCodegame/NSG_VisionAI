"""ML Model repository — Phase 4.9 / Phase 21"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_model import MLModel, ModelType
from app.repositories.base import BaseRepository


class MLModelRepository(BaseRepository[MLModel]):
    """Repository for MLModel — version tracking and deployment queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(MLModel, session)

    async def get_active_by_type(self, model_type: str) -> Optional[MLModel]:
        """Return the currently active model for a given type."""
        result = await self.session.execute(
            select(MLModel).where(
                MLModel.model_type == model_type,
                MLModel.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_type(
        self, model_type: str, skip: int = 0, limit: int = 50
    ) -> List[MLModel]:
        """Return all models of a given type, newest first."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=[MLModel.model_type == model_type],
            order_by=MLModel.created_at.desc(),
        )

    async def get_all_active(self) -> List[MLModel]:
        """Return one active model per type."""
        result = await self.session.execute(
            select(MLModel).where(MLModel.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def deactivate_all_of_type(self, model_type: str) -> None:
        """Deactivate every model of a given type (before deploying a new one)."""
        models = await self.get_by_type(model_type)
        for model in models:
            if model.is_active:
                await self.update(model.id, is_active=False)
