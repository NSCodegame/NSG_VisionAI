"""Audit Log repository (Read-Only)"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Repository for AuditLog model (Read-Only).
    
    IMPORTANT: This repository only supports create() and read operations.
    Update and delete operations are blocked at the database level by rules.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    # Override update and delete to prevent accidental calls
    async def update(self, id: UUID, **kwargs: Any) -> None:
        """Update is not allowed on audit logs"""
        raise NotImplementedError("Audit logs are immutable. Update operations are not allowed.")

    async def delete(self, id: UUID) -> None:
        """Delete is not allowed on audit logs"""
        raise NotImplementedError("Audit logs are immutable. Delete operations are not allowed.")

    async def get_by_user(
        self,
        user_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs by user"""
        filters = [AuditLog.user_id == user_id]

        if start_time:
            filters.append(AuditLog.timestamp >= start_time)
        if end_time:
            filters.append(AuditLog.timestamp <= end_time)

        result = await self.session.execute(
            select(AuditLog)
            .where(and_(*filters))
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self, action: str, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs by action"""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs by resource"""
        filters = [AuditLog.resource_type == resource_type]

        if resource_id:
            filters.append(AuditLog.resource_id == resource_id)

        result = await self.session.execute(
            select(AuditLog)
            .where(and_(*filters))
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def export_to_csv(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[UUID] = None,
        filters: Optional[List[Any]] = None,
    ) -> bytes:
        """
        Export audit logs to CSV bytes.

        Args:
            start_time: Optional start timestamp filter
            end_time: Optional end timestamp filter
            user_id: Optional user filter
            filters: Optional list of SQLAlchemy filter expressions (overrides other filters)

        Returns:
            CSV content as bytes
        """
        import csv
        import io

        if filters is None:
            filters = []
            if start_time:
                filters.append(AuditLog.timestamp >= start_time)
            if end_time:
                filters.append(AuditLog.timestamp <= end_time)
            if user_id:
                filters.append(AuditLog.user_id == user_id)

        query = select(AuditLog).order_by(AuditLog.timestamp.asc())
        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        logs = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "user_id", "action", "resource_type", "resource_id",
            "ip_address", "user_agent", "session_id", "timestamp", "details",
        ])
        for log in logs:
            writer.writerow([
                str(log.id),
                str(log.user_id) if log.user_id else "",
                log.action or "",
                log.resource_type or "",
                str(log.resource_id) if log.resource_id else "",
                str(log.ip_address) if log.ip_address else "",
                log.user_agent or "",
                str(log.session_id) if log.session_id else "",
                log.timestamp.isoformat() if log.timestamp else "",
                str(log.details) if log.details else "",
            ])

        return output.getvalue().encode("utf-8")
