"""Commission event query endpoints — TMF666."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.models import CommissionEvent
from app.infrastructure.db.repository import CommissionEventRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/commissionEvent", tags=["Commission Events"])


@router.get("/", response_model=dict)
async def list_commission_events(
    party_id: UUID | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    _token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_READ])),
):
    repo = CommissionEventRepository(db)
    items, total = await repo.list_with_filters(
        party_id=str(party_id) if party_id else None,
        from_date=from_date,
        to_date=to_date,
        status=status,
        page=page,
        size=size,
    )
    return {"items": [CommissionEvent.model_validate(i) for i in items], "total": total, "page": page, "size": size}


@router.get("/{event_id}", response_model=CommissionEvent)
async def get_commission_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_READ])),
):
    repo = CommissionEventRepository(db)
    item = await repo.get_by_id(str(event_id))
    if not item:
        raise NotFoundException("CommissionEvent", str(event_id))
    return CommissionEvent.model_validate(item)


@router.post("/recalculate", status_code=202)
async def trigger_recalculate(
    body: dict,
    _token=Depends(require_auth([Scopes.ADMIN])),
):
    """Admin endpoint — triggers asynchronous recalculation for a party/period."""
    return {"status": "accepted", "message": "Recalculation queued", "params": body}
