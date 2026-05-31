"""API endpoints for PerformanceMeasurement (TMF628)."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Query

from app.dependencies import DbSession, TenantId
from app.domain.models import PerformanceMeasurement
from app.infrastructure.db.repository import MeasurementRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/performanceMeasurement", tags=["Measurement"])


@router.get("", response_model=list[PerformanceMeasurement])
async def list_measurements(
    db: DbSession,
    tenant_id: TenantId,
    party_id: uuid.UUID | None = Query(default=None),
    kpi_spec_id: uuid.UUID | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
) -> list[PerformanceMeasurement]:
    repo = MeasurementRepository(db)
    return await repo.list_with_filters(
        tenant_id=tenant_id,
        party_id=party_id,
        kpi_spec_id=kpi_spec_id,
        from_date=from_date,
        to_date=to_date,
    )
