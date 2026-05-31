"""TMF632 Party Management API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import (
    CorrelationId,
    DbSession,
    KafkaProducerDep,
    TenantId,
    get_correlation_id,
    get_current_tenant_id,
    get_db,
    get_kafka_producer,
)
from app.domain.models import Party, PartyCreate, PartyRole, PartyStatus, PartyUpdate
from app.domain import services
from app.infrastructure.db.repository import PartyRepository
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/party", tags=["Party"])


@router.get("/", response_model=list[Party])
async def list_parties(
    role: PartyRole | None = Query(default=None, description="Filter by role"),
    status: PartyStatus | None = Query(default=None, description="Filter by status"),
    parent_party_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> list[Party]:
    """List parties with optional filters."""
    repo = PartyRepository(db)
    items = await repo.list_with_filters(
        tenant_id=tenant_id,
        role=role,
        status=status,
        parent_party_id=parent_party_id,
        page=page,
        size=size,
    )
    return [Party.model_validate(item) for item in items]


@router.post("/", response_model=Party, status_code=status.HTTP_201_CREATED)
async def create_party(
    body: PartyCreate,
    region: str | None = Query(default=None, description="Dealer region (published in event)"),
    tier: str | None = Query(default=None, description="Dealer tier (published in event)"),
    tenant_id: TenantId = Depends(get_current_tenant_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
    db: DbSession = Depends(get_db),
    kafka_producer: KafkaProducerDep = Depends(get_kafka_producer),
) -> Party:
    """Create (onboard) a new party.

    For DEALER parties a ``telco.party.dealer.onboarded`` CloudEvent is published.
    """
    repo = PartyRepository(db)
    party = await services.onboard_party(
        data=body,
        tenant_id=tenant_id,
        repo=repo,
        kafka_producer=kafka_producer,
        correlation_id=correlation_id,
        region=region,
        tier=tier,
    )
    return Party.model_validate(party)


@router.get("/{party_id}", response_model=Party)
async def get_party(
    party_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> Party:
    """Get a party by ID."""
    repo = PartyRepository(db)
    item = await repo.get_by_id(party_id=party_id, tenant_id=tenant_id)
    if item is None:
        raise NotFoundException("Party", str(party_id))
    return Party.model_validate(item)


@router.get("/{party_id}/hierarchy", response_model=list[Party])
async def get_party_hierarchy(
    party_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> list[Party]:
    """Return the party hierarchy from root to the specified party (root-first)."""
    repo = PartyRepository(db)
    hierarchy = await services.get_party_hierarchy(
        party_id=party_id,
        tenant_id=tenant_id,
        repo=repo,
    )
    return [Party.model_validate(item) for item in hierarchy]


@router.patch("/{party_id}", response_model=Party)
async def update_party(
    party_id: uuid.UUID,
    body: PartyUpdate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> Party:
    """Partially update a party."""
    repo = PartyRepository(db)
    item = await repo.update(party_id=party_id, tenant_id=tenant_id, data=body)
    if item is None:
        raise NotFoundException("Party", str(party_id))
    return Party.model_validate(item)


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_party(
    party_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> None:
    """Soft-delete a party (sets status to TERMINATED)."""
    repo = PartyRepository(db)
    item = await repo.soft_delete(party_id=party_id, tenant_id=tenant_id)
    if item is None:
        raise NotFoundException("Party", str(party_id))
