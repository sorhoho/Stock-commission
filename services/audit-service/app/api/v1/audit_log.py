from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.infrastructure.db.repository import AuditLogRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes

router = APIRouter(prefix="/auditLog", tags=["Audit Log"])


@router.get("/")
async def list_audit_logs(
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.AUDIT_READ])),
):
    repo = AuditLogRepository(db)
    items, total = await repo.query(token.tenant_id, event_type=event_type, from_date=from_date, to_date=to_date, page=page, size=size)
    return {"items": [{"id": str(i.id), "event_id": i.event_id, "event_type": i.event_type, "event_source": i.event_source, "tenant_id": i.tenant_id, "event_time": i.event_time, "received_at": i.received_at.isoformat()} for i in items], "total": total}
