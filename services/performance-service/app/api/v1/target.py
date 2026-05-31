"""API endpoints for PerformanceTarget (TMF628)."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession, TenantId
from app.domain.models import (
    PerformanceTarget,
    PerformanceTargetCreate,
    PerformanceTargetUpdate,
)
from app.infrastructure.db.repository import TargetRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/performanceTarget", tags=["Target"])


@router.post(
    "",
    response_model=PerformanceTarget,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    body: PerformanceTargetCreate,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceTarget:
    repo = TargetRepository(db)
    target = await repo.create(body, tenant_id)
    log.info("target.created", target_id=str(target.id), tenant_id=tenant_id)
    return target


@router.get("", response_model=list[PerformanceTarget])
async def list_targets(
    db: DbSession,
    tenant_id: TenantId,
    party_id: uuid.UUID | None = Query(default=None),
) -> list[PerformanceTarget]:
    repo = TargetRepository(db)
    return await repo.list_for_party(party_id=party_id, tenant_id=tenant_id)  # type: ignore[arg-type]


@router.get("/{target_id}", response_model=PerformanceTarget)
async def get_target(
    target_id: uuid.UUID,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceTarget:
    repo = TargetRepository(db)
    target = await repo.get_by_id(target_id, tenant_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PerformanceTarget '{target_id}' not found",
        )
    return target


@router.patch("/{target_id}", response_model=PerformanceTarget)
async def update_target(
    target_id: uuid.UUID,
    body: PerformanceTargetUpdate,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceTarget:
    repo = TargetRepository(db)
    target = await repo.update(target_id, body, tenant_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PerformanceTarget '{target_id}' not found",
        )
    return target
