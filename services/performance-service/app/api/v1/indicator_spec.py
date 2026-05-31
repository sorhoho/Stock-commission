"""API endpoints for PerformanceIndicatorSpec (TMF628)."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession, TenantId
from app.domain.models import (
    PerformanceIndicatorSpec,
    PerformanceIndicatorSpecCreate,
    PerformanceIndicatorSpecUpdate,
)
from app.infrastructure.db.repository import IndicatorSpecRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/performanceIndicatorSpec", tags=["IndicatorSpec"])


@router.post(
    "",
    response_model=PerformanceIndicatorSpec,
    status_code=status.HTTP_201_CREATED,
)
async def create_indicator_spec(
    body: PerformanceIndicatorSpecCreate,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceIndicatorSpec:
    repo = IndicatorSpecRepository(db)
    spec = await repo.create(body, tenant_id)
    log.info("indicator_spec.created", spec_id=str(spec.id), tenant_id=tenant_id)
    return spec


@router.get("", response_model=list[PerformanceIndicatorSpec])
async def list_indicator_specs(
    db: DbSession,
    tenant_id: TenantId,
) -> list[PerformanceIndicatorSpec]:
    repo = IndicatorSpecRepository(db)
    return await repo.list_all(tenant_id)


@router.get("/{spec_id}", response_model=PerformanceIndicatorSpec)
async def get_indicator_spec(
    spec_id: uuid.UUID,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceIndicatorSpec:
    repo = IndicatorSpecRepository(db)
    spec = await repo.get_by_id(spec_id, tenant_id)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PerformanceIndicatorSpec '{spec_id}' not found",
        )
    return spec


@router.patch("/{spec_id}", response_model=PerformanceIndicatorSpec)
async def update_indicator_spec(
    spec_id: uuid.UUID,
    body: PerformanceIndicatorSpecUpdate,
    db: DbSession,
    tenant_id: TenantId,
) -> PerformanceIndicatorSpec:
    repo = IndicatorSpecRepository(db)
    spec = await repo.update(spec_id, body, tenant_id)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PerformanceIndicatorSpec '{spec_id}' not found",
        )
    return spec
