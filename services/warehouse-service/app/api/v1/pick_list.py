"""Pick List API — outbound order fulfilment tasks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Query, status

from app.dependencies import DbSession, KafkaProducerDep, TenantId
from app.domain.models import (
    PickList,
    PickListAssign,
    PickListComplete,
    PickListCreate,
    PickListStatus,
)
from app.infrastructure.db.repository import PickListRepository
from telco_common.exceptions import NotFoundException, UnprocessableEntityException

router = APIRouter(prefix="/pickList", tags=["PickList"])


@router.post("/", response_model=PickList, status_code=status.HTTP_201_CREATED)
async def create_pick_list(
    body: PickListCreate,
    tenant_id: TenantId,
    db: DbSession,
) -> PickList:
    """Create a pick list for a sell-out or replenishment order."""
    repo = PickListRepository(db)
    pick_list = await repo.create(body, tenant_id)
    return _to_pydantic(pick_list)


@router.get("/", response_model=list[PickList])
async def list_pick_lists(
    status: PickListStatus | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId = ...,
    db: DbSession = ...,
) -> list[PickList]:
    repo = PickListRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id, status=status, assigned_to=assigned_to, page=page, size=size
    )
    return [_to_pydantic(p) for p in items]


@router.get("/{pick_list_id}", response_model=PickList)
async def get_pick_list(pick_list_id: uuid.UUID, tenant_id: TenantId, db: DbSession) -> PickList:
    repo = PickListRepository(db)
    pl = await repo.get_by_id(pick_list_id, tenant_id)
    if pl is None:
        raise NotFoundException("PickList", str(pick_list_id))
    return _to_pydantic(pl)


@router.post("/{pick_list_id}/assign", response_model=PickList)
async def assign_pick_list(
    pick_list_id: uuid.UUID,
    body: PickListAssign,
    tenant_id: TenantId,
    db: DbSession,
) -> PickList:
    """Assign a pick list to a warehouse worker."""
    repo = PickListRepository(db)
    pl = await repo.get_by_id(pick_list_id, tenant_id)
    if pl is None:
        raise NotFoundException("PickList", str(pick_list_id))
    if pl.status not in (PickListStatus.PENDING, PickListStatus.ASSIGNED):
        raise UnprocessableEntityException(f"Cannot assign pick list in status={pl.status}")
    updated = await repo.assign(pick_list_id, tenant_id, body.assigned_to)
    return _to_pydantic(updated)


@router.post("/{pick_list_id}/complete", response_model=PickList)
async def complete_pick_list(
    pick_list_id: uuid.UUID,
    body: PickListComplete,
    tenant_id: TenantId,
    db: DbSession,
) -> PickList:
    """Confirm actual quantities picked for each item."""
    repo = PickListRepository(db)
    pl = await repo.get_by_id(pick_list_id, tenant_id)
    if pl is None:
        raise NotFoundException("PickList", str(pick_list_id))
    if pl.status == PickListStatus.COMPLETED:
        raise UnprocessableEntityException("Pick list is already COMPLETED")
    item_picks = {item.item_id: item.picked_quantity for item in body.items}
    updated = await repo.complete(pick_list_id, tenant_id, item_picks)
    return _to_pydantic(updated)


def _to_pydantic(orm_obj) -> PickList:
    from app.domain.models import PickListItem as ItemModel
    pl = PickList.model_validate(orm_obj)
    pl.items = [ItemModel.model_validate(i) for i in (orm_obj.items or [])]
    return pl
