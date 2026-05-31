"""Dashboard endpoint — composite performance view for a party/period (TMF628)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession, TenantId
from app.domain.models import PerformanceDashboard
from app.infrastructure.db.repository import MeasurementRepository, TargetRepository

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/performanceDashboard", tags=["Dashboard"])


def _compute_summary(
    measurements: list,
    targets: list,
) -> dict[str, Any]:
    """Compute KPI variance: (measured - target) / target for each KPI spec."""
    target_map: dict[str, float] = {}
    for t in targets:
        key = str(t.kpi_spec_id)
        target_map[key] = t.target_value

    summary: dict[str, Any] = {}
    for m in measurements:
        key = str(m.kpi_spec_id)
        target_val = target_map.get(key)
        if target_val and target_val != 0:
            variance_pct = round(
                (m.measured_value - target_val) / target_val * 100, 2
            )
            summary[key] = {
                "kpi_spec_id": key,
                "measured_value": m.measured_value,
                "target_value": target_val,
                "variance_pct": variance_pct,
                "achieved": m.measured_value >= target_val,
            }
        else:
            summary[key] = {
                "kpi_spec_id": key,
                "measured_value": m.measured_value,
                "target_value": None,
                "variance_pct": None,
                "achieved": None,
            }
    return summary


@router.get("", response_model=PerformanceDashboard)
async def get_dashboard(
    db: DbSession,
    tenant_id: TenantId,
    party_id: uuid.UUID = Query(...),
    period: date = Query(..., description="First day of the desired month (YYYY-MM-01)"),
) -> PerformanceDashboard:
    """Return composite performance dashboard for a party within a period."""
    period_start = date(period.year, period.month, 1)

    meas_repo = MeasurementRepository(db)
    target_repo = TargetRepository(db)

    measurements = await meas_repo.list_with_filters(
        tenant_id=tenant_id,
        party_id=party_id,
        from_date=period_start,
        to_date=period_start,
    )
    targets = await target_repo.list_for_party(
        party_id=party_id,
        tenant_id=tenant_id,
        period=period_start,
    )

    summary = _compute_summary(measurements, targets)

    return PerformanceDashboard(
        party_id=party_id,
        period=period_start,
        measurements=measurements,
        targets=targets,
        summary=summary,
    )
