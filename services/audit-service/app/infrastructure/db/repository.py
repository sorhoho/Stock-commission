from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, entry: AuditLog) -> None:
        stmt = insert(AuditLog).values(
            id=entry.id,
            event_id=entry.event_id,
            event_type=entry.event_type,
            event_source=entry.event_source,
            tenant_id=entry.tenant_id,
            correlation_id=entry.correlation_id,
            event_time=entry.event_time,
            payload=entry.payload,
        ).on_conflict_do_nothing(constraint="uq_audit_log_event_id")
        await self._session.execute(stmt)

    async def query(
        self,
        tenant_id: str,
        event_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        q = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if event_type:
            q = q.where(AuditLog.event_type == event_type)
        q_count = q
        from sqlalchemy import func
        count_result = await self._session.execute(select(func.count()).select_from(q_count.subquery()))
        total = count_result.scalar_one()
        q = q.order_by(AuditLog.received_at.desc()).offset((page - 1) * size).limit(size)
        result = await self._session.execute(q)
        return list(result.scalars()), total
