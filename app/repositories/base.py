"""Base repository with generic CRUD operations"""
from typing import Any, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with generic async CRUD operations"""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository with model and session.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[List[Any]] = None,
        order_by: Optional[Any] = None,
    ) -> List[ModelType]:
        """
        Get multiple records with pagination, filtering, and sorting.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            filters: List of SQLAlchemy filter expressions
            order_by: SQLAlchemy order_by expression

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Apply filters
        if filters:
            for filter_expr in filters:
                query = query.where(filter_expr)

        # Apply ordering
        if order_by is not None:
            query = query.order_by(order_by)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs: Any) -> Optional[ModelType]:
        """
        Update an existing record.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get(id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, filters: Optional[List[Any]] = None) -> int:
        """
        Count records with optional filtering.

        Args:
            filters: List of SQLAlchemy filter expressions

        Returns:
            Number of records
        """
        query = select(func.count()).select_from(self.model)

        if filters:
            for filter_expr in filters:
                query = query.where(filter_expr)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        count = result.scalar_one()
        return count > 0
