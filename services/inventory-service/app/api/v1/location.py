"""TMF637-aligned Location API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, TenantId, get_db, get_current_tenant_id
from app.domain.models import Location, LocationCreate, LocationType, LocationUpdate
from app.infrastructure.db.repository import LocationRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/", response_model=list[Location])
async def list_locations(
    type: LocationType | None = Query(default=None, description="Filter by location type"),
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> list[Location]:
    """List all locations for the current tenant."""
    repo = LocationRepository(db)
    items = await repo.list(tenant_id=tenant_id, type_filter=type)
    return [Location.model_validate(item) for item in items]


@router.post("/", response_model=Location, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> Location:
    """Create a new location."""
    repo = LocationRepository(db)
    item = await repo.create(data=body, tenant_id=tenant_id)
    return Location.model_validate(item)


@router.get("/{location_id}", response_model=Location)
async def get_location(
    location_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> Location:
    """Get a location by ID."""
    repo = LocationRepository(db)
    item = await repo.get_by_id(location_id=location_id, tenant_id=tenant_id)
    if item is None:
        raise NotFoundException("Location", str(location_id))
    return Location.model_validate(item)


@router.patch("/{location_id}", response_model=Location)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> Location:
    """Partially update a location."""
    repo = LocationRepository(db)
    item = await repo.update(location_id=location_id, tenant_id=tenant_id, data=body)
    if item is None:
        raise NotFoundException("Location", str(location_id))
    return Location.model_validate(item)
