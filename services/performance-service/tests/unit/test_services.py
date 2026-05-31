"""Unit tests for performance-service repositories and dashboard logic."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    IndicatorType,
    MeasurementInterval,
    PerformanceIndicatorSpec,
    PerformanceMeasurement,
    PerformanceTarget,
    PerformanceTargetCreate,
    TargetStatus,
)
from app.api.v1.dashboard import _compute_summary


# ── IndicatorSpecRepository ───────────────────────────────────────────────────


class TestIndicatorSpecRepository:
    @pytest.mark.asyncio
    async def test_create_returns_pydantic_model(
        self, mock_db_session, sample_tenant_id, sample_indicator_spec_data
    ):
        from app.domain.models import PerformanceIndicatorSpecCreate
        from app.infrastructure.db.repository import IndicatorSpecRepository

        spec_id = uuid.uuid4()

        # Simulate the ORM object returned after flush/refresh
        orm_obj = MagicMock()
        orm_obj.id = spec_id
        orm_obj.name = sample_indicator_spec_data["name"]
        orm_obj.description = sample_indicator_spec_data["description"]
        orm_obj.unit_of_measure = sample_indicator_spec_data["unit_of_measure"]
        orm_obj.indicator_type = sample_indicator_spec_data["indicator_type"]
        orm_obj.measurement_interval = sample_indicator_spec_data["measurement_interval"]
        orm_obj.tenant_id = sample_tenant_id
        orm_obj.created_at = date.today()
        orm_obj.updated_at = date.today()

        mock_db_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, "id", spec_id)
        )

        with patch(
            "app.infrastructure.db.repository.PerformanceIndicatorSpecDB",
            return_value=orm_obj,
        ):
            repo = IndicatorSpecRepository(mock_db_session)
            create_data = PerformanceIndicatorSpecCreate(**sample_indicator_spec_data)

            # Patch model_validate to work with mock
            with patch.object(
                PerformanceIndicatorSpec,
                "model_validate",
                return_value=PerformanceIndicatorSpec(
                    id=spec_id,
                    name=orm_obj.name,
                    description=orm_obj.description,
                    unit_of_measure=orm_obj.unit_of_measure,
                    indicator_type=orm_obj.indicator_type,
                    measurement_interval=orm_obj.measurement_interval,
                    tenant_id=sample_tenant_id,
                    created_at=date.today(),
                    updated_at=date.today(),
                ),
            ):
                result = await repo.create(create_data, sample_tenant_id)

        assert result.name == sample_indicator_spec_data["name"]
        assert result.tenant_id == sample_tenant_id
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()


# ── TargetRepository ──────────────────────────────────────────────────────────


class TestTargetRepository:
    @pytest.mark.asyncio
    async def test_update_status_calls_execute(
        self, mock_db_session, sample_tenant_id
    ):
        from app.infrastructure.db.repository import TargetRepository

        target_id = uuid.uuid4()
        repo = TargetRepository(mock_db_session)

        await repo.update_status(target_id, TargetStatus.ACHIEVED, sample_tenant_id)

        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_missing(
        self, mock_db_session, sample_tenant_id
    ):
        from app.infrastructure.db.repository import TargetRepository

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        repo = TargetRepository(mock_db_session)
        result = await repo.get_by_id(uuid.uuid4(), sample_tenant_id)

        assert result is None


# ── Dashboard summary computation ────────────────────────────────────────────


class TestDashboardSummary:
    def _make_measurement(self, kpi_spec_id: uuid.UUID, value: float) -> PerformanceMeasurement:
        return PerformanceMeasurement(
            id=uuid.uuid4(),
            party_id=uuid.uuid4(),
            kpi_spec_id=kpi_spec_id,
            period=date(2025, 1, 1),
            measured_value=value,
            source_event_ids=["evt-1"],
            tenant_id="t1",
            created_at=date.today(),  # type: ignore[arg-type]
        )

    def _make_target(self, kpi_spec_id: uuid.UUID, target_value: float) -> PerformanceTarget:
        return PerformanceTarget(
            id=uuid.uuid4(),
            party_id=uuid.uuid4(),
            kpi_spec_id=kpi_spec_id,
            target_value=target_value,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status=TargetStatus.ACTIVE,
            tenant_id="t1",
            created_at=date.today(),  # type: ignore[arg-type]
            updated_at=date.today(),  # type: ignore[arg-type]
        )

    def test_compute_summary_achieved(self):
        kpi_id = uuid.uuid4()
        measurements = [self._make_measurement(kpi_id, 120.0)]
        targets = [self._make_target(kpi_id, 100.0)]
        summary = _compute_summary(measurements, targets)
        entry = summary[str(kpi_id)]
        assert entry["achieved"] is True
        assert entry["variance_pct"] == 20.0

    def test_compute_summary_not_achieved(self):
        kpi_id = uuid.uuid4()
        measurements = [self._make_measurement(kpi_id, 80.0)]
        targets = [self._make_target(kpi_id, 100.0)]
        summary = _compute_summary(measurements, targets)
        entry = summary[str(kpi_id)]
        assert entry["achieved"] is False
        assert entry["variance_pct"] == -20.0

    def test_compute_summary_no_target(self):
        kpi_id = uuid.uuid4()
        measurements = [self._make_measurement(kpi_id, 50.0)]
        summary = _compute_summary(measurements, [])
        entry = summary[str(kpi_id)]
        assert entry["target_value"] is None
        assert entry["achieved"] is None
