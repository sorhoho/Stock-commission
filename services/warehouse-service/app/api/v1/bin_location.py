"""Bin Location API — warehouse zone/aisle/rack/bin management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.dependencies import DbSession, TenantId
from app.domain.models import BinLocation, BinLocationCreate
from app.infrastructure.db.repository import BinLocationRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/binLocation", tags=["BinLocation"])


@router.post("/", response_model=BinLocation, status_code=status.HTTP_201_CREATED)
async def create_bin_location(
    body: BinLocationCreate,
    tenant_id: TenantId,
    db: DbSession,
) -> BinLocation:
    """Create a bin/slot within a warehouse location."""
    repo = BinLocationRepository(db)
    bin_loc = await repo.create(body, tenant_id)
    return BinLocation.model_validate(bin_loc)


@router.get("/", response_model=list[BinLocation])
async def list_bin_locations(
    location_id: uuid.UUID | None = Query(default=None),
    zone: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    tenant_id: TenantId = ...,
    db: DbSession = ...,
) -> list[BinLocation]:
    """List bin locations with optional filters."""
    repo = BinLocationRepository(db)
    bins = await repo.list_with_filters(
        tenant_id=tenant_id, location_id=location_id, zone=zone, page=page, size=size
    )
    return [BinLocation.model_validate(b) for b in bins]


@router.get("/{bin_id}", response_model=BinLocation)
async def get_bin_location(bin_id: uuid.UUID, tenant_id: TenantId, db: DbSession) -> BinLocation:
    repo = BinLocationRepository(db)
    bin_loc = await repo.get_by_id(bin_id, tenant_id)
    if bin_loc is None:
        raise NotFoundException("BinLocation", str(bin_id))
    return BinLocation.model_validate(bin_loc)
