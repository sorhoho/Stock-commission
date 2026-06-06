"""TMF 639 Resource Inventory API — individual device/SIM/serial tracking."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.dependencies import DbSession, TenantId
from app.domain.models import Resource, ResourceCreate, ResourceStatusType
from app.infrastructure.db.repository import ResourceRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/resource", tags=["ResourceInventory"])


@router.post("/", response_model=list[Resource], status_code=status.HTTP_201_CREATED)
async def register_resources(
    body: list[ResourceCreate],
    tenant_id: TenantId,
    db: DbSession,
) -> list[Resource]:
    """Bulk register resources (devices, SIMs) — typically called after a GRN."""
    repo = ResourceRepository(db)
    created = []
    for item in body:
        resource = await repo.create(item, tenant_id)
        created.append(resource)
    return [Resource.model_validate(r) for r in created]


@router.get("/", response_model=list[Resource])
async def list_resources(
    product_id: uuid.UUID | None = Query(default=None),
    status: ResourceStatusType | None = Query(default=None),
    inventory_id: uuid.UUID | None = Query(default=None),
    characteristic_name: str | None = Query(default=None),
    characteristic_value: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId = ...,
    db: DbSession = ...,
) -> list[Resource]:
    """List resources with optional filters. Supports IMEI/ICCID lookup via characteristicName/Value."""
    repo = ResourceRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id,
        product_id=product_id,
        status=status,
        inventory_id=inventory_id,
        characteristic_name=characteristic_name,
        characteristic_value=characteristic_value,
        page=page,
        size=size,
    )
    return [Resource.model_validate(r) for r in items]


@router.get("/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: uuid.UUID,
    tenant_id: TenantId,
    db: DbSession,
) -> Resource:
    """Get a resource by ID (TMF 639 GET /resource/{id})."""
    repo = ResourceRepository(db)
    resource = await repo.get_by_id(resource_id, tenant_id)
    if resource is None:
        raise NotFoundException("Resource", str(resource_id))
    return Resource.model_validate(resource)
