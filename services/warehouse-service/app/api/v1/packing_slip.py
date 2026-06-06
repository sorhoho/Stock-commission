"""Packing Slip API — pack and dispatch management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import DbSession, TenantId
from app.domain.models import PackingSlip, PackingSlipCreate, PackingSlipDispatch
from app.infrastructure.db.repository import PackingSlipRepository
from telco_common.exceptions import NotFoundException, UnprocessableEntityException

router = APIRouter(prefix="/packingSlip", tags=["PackingSlip"])


@router.post("/", response_model=PackingSlip, status_code=status.HTTP_201_CREATED)
async def create_packing_slip(
    body: PackingSlipCreate,
    tenant_id: TenantId,
    db: DbSession,
) -> PackingSlip:
    """Create a packing slip from a completed pick list."""
    repo = PackingSlipRepository(db)
    slip = await repo.create(body, tenant_id)
    return _to_pydantic(slip)


@router.get("/{slip_id}", response_model=PackingSlip)
async def get_packing_slip(slip_id: uuid.UUID, tenant_id: TenantId, db: DbSession) -> PackingSlip:
    repo = PackingSlipRepository(db)
    slip = await repo.get_by_id(slip_id, tenant_id)
    if slip is None:
        raise NotFoundException("PackingSlip", str(slip_id))
    return _to_pydantic(slip)


@router.post("/{slip_id}/dispatch", response_model=PackingSlip)
async def dispatch_packing_slip(
    slip_id: uuid.UUID,
    body: PackingSlipDispatch,
    tenant_id: TenantId,
    db: DbSession,
) -> PackingSlip:
    """Mark a packing slip as DISPATCHED with optional carrier and tracking number."""
    repo = PackingSlipRepository(db)
    slip = await repo.get_by_id(slip_id, tenant_id)
    if slip is None:
        raise NotFoundException("PackingSlip", str(slip_id))
    if slip.status != "PACKED":
        raise UnprocessableEntityException(f"Only PACKED slips can be dispatched (current={slip.status})")
    updated = await repo.dispatch(slip_id, tenant_id, body.shipping_carrier, body.tracking_number)
    return _to_pydantic(updated)


def _to_pydantic(orm_obj) -> PackingSlip:
    from app.domain.models import PackingSlipItem as ItemModel
    slip = PackingSlip.model_validate(orm_obj)
    slip.items = [ItemModel.model_validate(i) for i in (orm_obj.items or [])]
    return slip
