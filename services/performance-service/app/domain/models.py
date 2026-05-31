"""Pydantic v2 domain models for the Performance service (TMF628)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MeasurementInterval(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class IndicatorType(StrEnum):
    GAUGE = "GAUGE"
    COUNTER = "COUNTER"
    RATIO = "RATIO"


class TargetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ACHIEVED = "ACHIEVED"
    MISSED = "MISSED"


# ---------------------------------------------------------------------------
# PerformanceIndicatorSpec
# ---------------------------------------------------------------------------


class PerformanceIndicatorSpecCreate(BaseModel):
    name: str
    description: str | None = None
    unit_of_measure: str
    indicator_type: IndicatorType
    measurement_interval: MeasurementInterval


class PerformanceIndicatorSpecUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit_of_measure: str | None = None
    indicator_type: IndicatorType | None = None
    measurement_interval: MeasurementInterval | None = None


class PerformanceIndicatorSpec(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    unit_of_measure: str
    indicator_type: IndicatorType
    measurement_interval: MeasurementInterval
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PerformanceTarget
# ---------------------------------------------------------------------------


class PerformanceTargetCreate(BaseModel):
    party_id: uuid.UUID
    kpi_spec_id: uuid.UUID
    target_value: float
    period_start: date
    period_end: date


class PerformanceTargetUpdate(BaseModel):
    target_value: float | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: TargetStatus | None = None


class PerformanceTarget(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    kpi_spec_id: uuid.UUID
    target_value: float
    period_start: date
    period_end: date
    status: TargetStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PerformanceMeasurement
# ---------------------------------------------------------------------------


class PerformanceMeasurement(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    kpi_spec_id: uuid.UUID
    period: date
    measured_value: float
    source_event_ids: list[str]
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PerformanceDashboard (composite)
# ---------------------------------------------------------------------------


class PerformanceDashboard(BaseModel):
    party_id: uuid.UUID
    period: date
    measurements: list[PerformanceMeasurement]
    targets: list[PerformanceTarget]
    summary: dict[str, Any]  # computed KPI variance per spec
