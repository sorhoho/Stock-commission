"""Unit tests for performance-service API handlers."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.domain.models import (
    IndicatorType,
    MeasurementInterval,
    PerformanceDashboard,
    PerformanceIndicatorSpec,
    PerformanceIndicatorSpecCreate,
    PerformanceIndicatorSpecUpdate,
    PerformanceMeasurement,
    PerformanceTarget,
    PerformanceTargetCreate,
    PerformanceTargetUpdate,
    TargetStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT = "tenant-abc"
SPEC_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()
PARTY_ID = uuid.uuid4()
KPI_SPEC_ID = uuid.uuid4()


def _make_spec(spec_id: uuid.UUID | None = None) -> PerformanceIndicatorSpec:
    return PerformanceIndicatorSpec(
        id=spec_id or uuid.uuid4(),
        name="MONTHLY_REVENUE",
        description="Monthly revenue",
        unit_of_measure="USD",
        indicator_type=IndicatorType.GAUGE,
        measurement_interval=MeasurementInterval.MONTHLY,
        tenant_id=TENANT,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


def _make_target(target_id: uuid.UUID | None = None) -> PerformanceTarget:
    return PerformanceTarget(
        id=target_id or uuid.uuid4(),
        party_id=PARTY_ID,
        kpi_spec_id=KPI_SPEC_ID,
        target_value=1000.0,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        status=TargetStatus.ACTIVE,
        tenant_id=TENANT,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


def _make_measurement(kpi_spec_id: uuid.UUID | None = None, value: float = 900.0) -> PerformanceMeasurement:
    return PerformanceMeasurement(
        id=uuid.uuid4(),
        party_id=PARTY_ID,
        kpi_spec_id=kpi_spec_id or KPI_SPEC_ID,
        period=date(2025, 1, 1),
        measured_value=value,
        source_event_ids=["evt-1"],
        tenant_id=TENANT,
        created_at=datetime(2025, 1, 1),
    )


# ---------------------------------------------------------------------------
# Dependencies tests
# ---------------------------------------------------------------------------


class TestDependencies:
    @pytest.mark.asyncio
    async def test_get_db_yields_session_and_commits(self):
        from app.dependencies import get_db

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session
            try:
                await gen.asend(None)
            except StopAsyncIteration:
                pass

        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self):
        from app.dependencies import get_db

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(RuntimeError):
                await gen.athrow(RuntimeError("db error"))

        mock_session.rollback.assert_awaited()
        mock_session.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_kafka_producer_returns_producer(self):
        from app.dependencies import get_kafka_producer

        mock_producer = AsyncMock()
        request = MagicMock()
        request.app.state.kafka_producer = mock_producer

        result = await get_kafka_producer(request)
        assert result is mock_producer

    @pytest.mark.asyncio
    async def test_get_kafka_producer_raises_503_when_missing(self):
        from app.dependencies import get_kafka_producer
        from fastapi import HTTPException

        request = MagicMock()
        request.app.state.kafka_producer = None

        with pytest.raises(HTTPException) as exc_info:
            await get_kafka_producer(request)
        assert exc_info.value.status_code == 503

    def test_get_current_tenant_id_returns_tenant(self):
        from app.dependencies import get_current_tenant_id

        request = MagicMock()
        request.state.tenant_id = "tenant-x"

        result = get_current_tenant_id(request)
        assert result == "tenant-x"

    def test_get_current_tenant_id_raises_400_when_missing(self):
        from app.dependencies import get_current_tenant_id
        from fastapi import HTTPException

        request = MagicMock()
        request.state.tenant_id = ""

        with pytest.raises(HTTPException) as exc_info:
            get_current_tenant_id(request)
        assert exc_info.value.status_code == 400

    def test_get_correlation_id_returns_value(self):
        from app.dependencies import get_correlation_id

        request = MagicMock()
        request.state.correlation_id = "corr-123"

        result = get_correlation_id(request)
        assert result == "corr-123"

    def test_get_correlation_id_returns_empty_when_missing(self):
        from app.dependencies import get_correlation_id

        request = MagicMock()
        # No correlation_id attribute on request.state
        del request.state.correlation_id
        type(request.state).__getattr__ = lambda self, name: ""

        result = get_correlation_id(request)
        assert result == ""


# ---------------------------------------------------------------------------
# Session get_db tests
# ---------------------------------------------------------------------------


class TestSessionGetDb:
    @pytest.mark.asyncio
    async def test_session_get_db_yields_and_commits(self):
        from app.infrastructure.db.session import get_db

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.db.session.AsyncSessionLocal", return_value=mock_ctx):
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session
            try:
                await gen.asend(None)
            except StopAsyncIteration:
                pass

        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_session_get_db_rollback_on_exception(self):
        from app.infrastructure.db.session import get_db

        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.db.session.AsyncSessionLocal", return_value=mock_ctx):
            gen = get_db()
            await gen.__anext__()
            with pytest.raises(RuntimeError):
                await gen.athrow(RuntimeError("session error"))

        mock_session.rollback.assert_awaited()
        mock_session.close.assert_awaited()


# ---------------------------------------------------------------------------
# SellOut consumer tests
# ---------------------------------------------------------------------------


class TestSellOutConsumer:
    """Tests for the sell-out Kafka event handler.

    The handler uses local (lazy) imports, so we patch at the source module level.
    """

    def _make_event(self, event_id: str = "evt-001", total_amount: float = 500.0, items: list | None = None) -> dict:
        return {
            "id": event_id,
            "data": {
                "transaction_id": f"txn-{event_id}",
                "transaction_number": f"TXN-{event_id}",
                "dealer_party_id": str(PARTY_ID),
                "dealer_name": "Test Dealer",
                "channel": "RETAIL",
                "sale_date": "2025-01-15",
                "total_amount": total_amount,
                "currency": "USD",
                "items": items or [],
                "tenant_id": TENANT,
            },
        }

    def _mock_session_local(self):
        """Return a mock AsyncSessionLocal callable yielding a mock session."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        # Make a context manager factory: AsyncSessionLocal() returns ctx
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        session_local = MagicMock(return_value=ctx)
        return mock_session, session_local

    @pytest.mark.asyncio
    async def test_handle_sell_out_event_with_no_matching_specs(self):
        """When no KPI specs exist, no measurements are upserted."""
        from app.infrastructure.kafka.consumers.sell_out_consumer import _handle_sell_out_event

        mock_session, mock_session_local = self._mock_session_local()

        mock_spec_repo = AsyncMock()
        mock_spec_repo.list_all.return_value = []
        mock_meas_repo = AsyncMock()
        mock_target_repo = AsyncMock()

        with patch("app.infrastructure.db.session.AsyncSessionLocal", mock_session_local), \
             patch("app.infrastructure.db.repository.IndicatorSpecRepository", return_value=mock_spec_repo), \
             patch("app.infrastructure.db.repository.MeasurementRepository", return_value=mock_meas_repo), \
             patch("app.infrastructure.db.repository.TargetRepository", return_value=mock_target_repo):
            await _handle_sell_out_event(self._make_event(items=[
                {"product_id": "p1", "product_name": "SIM", "quantity": 5, "unit_price": 100.0}
            ]), AsyncMock())

        mock_meas_repo.upsert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_sell_out_event_upserts_for_both_specs(self):
        """When both KPI specs exist, measurements are upserted for units and revenue."""
        from app.infrastructure.kafka.consumers.sell_out_consumer import (
            _handle_sell_out_event,
            KPI_UNITS_NAME,
            KPI_REVENUE_NAME,
        )

        units_spec = PerformanceIndicatorSpec(
            id=uuid.uuid4(), name=KPI_UNITS_NAME, unit_of_measure="units",
            indicator_type=IndicatorType.COUNTER, measurement_interval=MeasurementInterval.MONTHLY,
            tenant_id=TENANT, created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1),
        )
        revenue_spec = PerformanceIndicatorSpec(
            id=uuid.uuid4(), name=KPI_REVENUE_NAME, unit_of_measure="USD",
            indicator_type=IndicatorType.GAUGE, measurement_interval=MeasurementInterval.MONTHLY,
            tenant_id=TENANT, created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1),
        )

        mock_session, mock_session_local = self._mock_session_local()
        mock_spec_repo = AsyncMock()
        mock_spec_repo.list_all.return_value = [units_spec, revenue_spec]
        mock_meas_repo = AsyncMock()
        mock_meas_repo.upsert.return_value = _make_measurement(value=3.0)
        mock_target_repo = AsyncMock()
        mock_target_repo.get_active_for_party_and_spec.return_value = []

        with patch("app.infrastructure.db.session.AsyncSessionLocal", mock_session_local), \
             patch("app.infrastructure.db.repository.IndicatorSpecRepository", return_value=mock_spec_repo), \
             patch("app.infrastructure.db.repository.MeasurementRepository", return_value=mock_meas_repo), \
             patch("app.infrastructure.db.repository.TargetRepository", return_value=mock_target_repo):
            await _handle_sell_out_event(
                self._make_event("evt-002", 1500.0, [
                    {"product_id": "p1", "product_name": "SIM", "quantity": 3, "unit_price": 500.0}
                ]),
                AsyncMock(),
            )

        assert mock_meas_repo.upsert.await_count == 2

    @pytest.mark.asyncio
    async def test_handle_sell_out_event_updates_target_to_achieved(self):
        """When measurement >= target_value, target status becomes ACHIEVED."""
        from app.infrastructure.kafka.consumers.sell_out_consumer import (
            _handle_sell_out_event,
            KPI_REVENUE_NAME,
        )

        revenue_spec = PerformanceIndicatorSpec(
            id=KPI_SPEC_ID, name=KPI_REVENUE_NAME, unit_of_measure="USD",
            indicator_type=IndicatorType.GAUGE, measurement_interval=MeasurementInterval.MONTHLY,
            tenant_id=TENANT, created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1),
        )
        active_target = _make_target(TARGET_ID)
        measurement = _make_measurement(KPI_SPEC_ID, 2000.0)

        mock_session, mock_session_local = self._mock_session_local()
        mock_spec_repo = AsyncMock()
        mock_spec_repo.list_all.return_value = [revenue_spec]
        mock_meas_repo = AsyncMock()
        mock_meas_repo.upsert.return_value = measurement
        mock_target_repo = AsyncMock()
        mock_target_repo.get_active_for_party_and_spec.return_value = [active_target]

        with patch("app.infrastructure.db.session.AsyncSessionLocal", mock_session_local), \
             patch("app.infrastructure.db.repository.IndicatorSpecRepository", return_value=mock_spec_repo), \
             patch("app.infrastructure.db.repository.MeasurementRepository", return_value=mock_meas_repo), \
             patch("app.infrastructure.db.repository.TargetRepository", return_value=mock_target_repo):
            await _handle_sell_out_event(self._make_event("evt-003", 2000.0), AsyncMock())

        mock_target_repo.update_status.assert_awaited_once_with(
            target_id=TARGET_ID,
            status=TargetStatus.ACHIEVED,
            tenant_id=TENANT,
        )

    @pytest.mark.asyncio
    async def test_handle_sell_out_event_updates_target_to_missed_when_past_period(self):
        """When period > target.period_end and below target, status becomes MISSED."""
        from app.infrastructure.kafka.consumers.sell_out_consumer import (
            _handle_sell_out_event,
            KPI_REVENUE_NAME,
        )

        revenue_spec = PerformanceIndicatorSpec(
            id=KPI_SPEC_ID, name=KPI_REVENUE_NAME, unit_of_measure="USD",
            indicator_type=IndicatorType.GAUGE, measurement_interval=MeasurementInterval.MONTHLY,
            tenant_id=TENANT, created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1),
        )
        # Target ended Dec 2024; sale_date 2025-01-15 → period 2025-01-01 > period_end
        missed_target = PerformanceTarget(
            id=TARGET_ID, party_id=PARTY_ID, kpi_spec_id=KPI_SPEC_ID,
            target_value=5000.0,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 31),
            status=TargetStatus.ACTIVE,
            tenant_id=TENANT,
            created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1),
        )
        measurement = _make_measurement(KPI_SPEC_ID, 100.0)

        mock_session, mock_session_local = self._mock_session_local()
        mock_spec_repo = AsyncMock()
        mock_spec_repo.list_all.return_value = [revenue_spec]
        mock_meas_repo = AsyncMock()
        mock_meas_repo.upsert.return_value = measurement
        mock_target_repo = AsyncMock()
        mock_target_repo.get_active_for_party_and_spec.return_value = [missed_target]

        with patch("app.infrastructure.db.session.AsyncSessionLocal", mock_session_local), \
             patch("app.infrastructure.db.repository.IndicatorSpecRepository", return_value=mock_spec_repo), \
             patch("app.infrastructure.db.repository.MeasurementRepository", return_value=mock_meas_repo), \
             patch("app.infrastructure.db.repository.TargetRepository", return_value=mock_target_repo):
            await _handle_sell_out_event(self._make_event("evt-004", 100.0), AsyncMock())

        mock_target_repo.update_status.assert_awaited_once_with(
            target_id=TARGET_ID,
            status=TargetStatus.MISSED,
            tenant_id=TENANT,
        )


# ---------------------------------------------------------------------------
# Router import test
# ---------------------------------------------------------------------------


class TestRouter:
    def test_router_has_correct_prefix(self):
        from app.api.v1.router import router
        assert router.prefix == "/api/v1/performanceManagement"

    def test_router_includes_sub_routers(self):
        from app.api.v1.router import router
        prefixes = {r.prefix for r in router.routes if hasattr(r, "prefix")}
        # The included sub-routers mount under the main router; the routes
        # themselves live at their final paths
        assert len(router.routes) > 0


# ---------------------------------------------------------------------------
# IndicatorSpec API
# ---------------------------------------------------------------------------


class TestIndicatorSpecAPI:
    @pytest.mark.asyncio
    async def test_create_indicator_spec_returns_spec(self):
        from app.api.v1.indicator_spec import create_indicator_spec

        expected = _make_spec(SPEC_ID)
        body = PerformanceIndicatorSpecCreate(
            name="MONTHLY_REVENUE",
            unit_of_measure="USD",
            indicator_type=IndicatorType.GAUGE,
            measurement_interval=MeasurementInterval.MONTHLY,
        )

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.create.return_value = expected
            MockRepo.return_value = instance

            result = await create_indicator_spec(
                body=body,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.create.assert_awaited_once_with(body, TENANT)

    @pytest.mark.asyncio
    async def test_list_indicator_specs_returns_list(self):
        from app.api.v1.indicator_spec import list_indicator_specs

        specs = [_make_spec(), _make_spec()]

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_all.return_value = specs
            MockRepo.return_value = instance

            result = await list_indicator_specs(db=AsyncMock(), tenant_id=TENANT)

        assert result == specs
        instance.list_all.assert_awaited_once_with(TENANT)

    @pytest.mark.asyncio
    async def test_get_indicator_spec_returns_spec(self):
        from app.api.v1.indicator_spec import get_indicator_spec

        expected = _make_spec(SPEC_ID)

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = expected
            MockRepo.return_value = instance

            result = await get_indicator_spec(
                spec_id=SPEC_ID,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.get_by_id.assert_awaited_once_with(SPEC_ID, TENANT)

    @pytest.mark.asyncio
    async def test_get_indicator_spec_raises_404_when_missing(self):
        from app.api.v1.indicator_spec import get_indicator_spec

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = None
            MockRepo.return_value = instance

            with pytest.raises(HTTPException) as exc_info:
                await get_indicator_spec(
                    spec_id=SPEC_ID,
                    db=AsyncMock(),
                    tenant_id=TENANT,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_indicator_spec_returns_updated(self):
        from app.api.v1.indicator_spec import update_indicator_spec

        expected = _make_spec(SPEC_ID)
        body = PerformanceIndicatorSpecUpdate(name="UPDATED_NAME")

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.update.return_value = expected
            MockRepo.return_value = instance

            result = await update_indicator_spec(
                spec_id=SPEC_ID,
                body=body,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.update.assert_awaited_once_with(SPEC_ID, body, TENANT)

    @pytest.mark.asyncio
    async def test_update_indicator_spec_raises_404_when_missing(self):
        from app.api.v1.indicator_spec import update_indicator_spec

        body = PerformanceIndicatorSpecUpdate(name="UPDATED_NAME")

        with patch("app.api.v1.indicator_spec.IndicatorSpecRepository") as MockRepo:
            instance = AsyncMock()
            instance.update.return_value = None
            MockRepo.return_value = instance

            with pytest.raises(HTTPException) as exc_info:
                await update_indicator_spec(
                    spec_id=SPEC_ID,
                    body=body,
                    db=AsyncMock(),
                    tenant_id=TENANT,
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Measurement API
# ---------------------------------------------------------------------------


class TestMeasurementAPI:
    @pytest.mark.asyncio
    async def test_list_measurements_no_filters(self):
        from app.api.v1.measurement import list_measurements

        measurements = [_make_measurement(), _make_measurement()]

        with patch("app.api.v1.measurement.MeasurementRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_with_filters.return_value = measurements
            MockRepo.return_value = instance

            result = await list_measurements(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=None,
                kpi_spec_id=None,
                from_date=None,
                to_date=None,
            )

        assert result == measurements
        instance.list_with_filters.assert_awaited_once_with(
            tenant_id=TENANT,
            party_id=None,
            kpi_spec_id=None,
            from_date=None,
            to_date=None,
        )

    @pytest.mark.asyncio
    async def test_list_measurements_with_filters(self):
        from app.api.v1.measurement import list_measurements

        measurements = [_make_measurement()]
        from_date = date(2025, 1, 1)
        to_date = date(2025, 1, 31)

        with patch("app.api.v1.measurement.MeasurementRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_with_filters.return_value = measurements
            MockRepo.return_value = instance

            result = await list_measurements(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                from_date=from_date,
                to_date=to_date,
            )

        assert result == measurements
        instance.list_with_filters.assert_awaited_once_with(
            tenant_id=TENANT,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            from_date=from_date,
            to_date=to_date,
        )

    @pytest.mark.asyncio
    async def test_list_measurements_returns_empty_list(self):
        from app.api.v1.measurement import list_measurements

        with patch("app.api.v1.measurement.MeasurementRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_with_filters.return_value = []
            MockRepo.return_value = instance

            result = await list_measurements(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=None,
                kpi_spec_id=None,
                from_date=None,
                to_date=None,
            )

        assert result == []


# ---------------------------------------------------------------------------
# Target API
# ---------------------------------------------------------------------------


class TestTargetAPI:
    @pytest.mark.asyncio
    async def test_create_target_returns_target(self):
        from app.api.v1.target import create_target

        expected = _make_target(TARGET_ID)
        body = PerformanceTargetCreate(
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            target_value=1000.0,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.create.return_value = expected
            MockRepo.return_value = instance

            result = await create_target(
                body=body,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.create.assert_awaited_once_with(body, TENANT)

    @pytest.mark.asyncio
    async def test_list_targets_no_filter(self):
        from app.api.v1.target import list_targets

        targets = [_make_target(), _make_target()]

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_for_party.return_value = targets
            MockRepo.return_value = instance

            result = await list_targets(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=None,
            )

        assert result == targets
        instance.list_for_party.assert_awaited_once_with(party_id=None, tenant_id=TENANT)

    @pytest.mark.asyncio
    async def test_list_targets_with_party_filter(self):
        from app.api.v1.target import list_targets

        targets = [_make_target()]

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.list_for_party.return_value = targets
            MockRepo.return_value = instance

            result = await list_targets(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
            )

        assert result == targets
        instance.list_for_party.assert_awaited_once_with(party_id=PARTY_ID, tenant_id=TENANT)

    @pytest.mark.asyncio
    async def test_get_target_returns_target(self):
        from app.api.v1.target import get_target

        expected = _make_target(TARGET_ID)

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = expected
            MockRepo.return_value = instance

            result = await get_target(
                target_id=TARGET_ID,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.get_by_id.assert_awaited_once_with(TARGET_ID, TENANT)

    @pytest.mark.asyncio
    async def test_get_target_raises_404_when_missing(self):
        from app.api.v1.target import get_target

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = None
            MockRepo.return_value = instance

            with pytest.raises(HTTPException) as exc_info:
                await get_target(
                    target_id=TARGET_ID,
                    db=AsyncMock(),
                    tenant_id=TENANT,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_target_returns_updated(self):
        from app.api.v1.target import update_target

        expected = _make_target(TARGET_ID)
        body = PerformanceTargetUpdate(target_value=2000.0)

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.update.return_value = expected
            MockRepo.return_value = instance

            result = await update_target(
                target_id=TARGET_ID,
                body=body,
                db=AsyncMock(),
                tenant_id=TENANT,
            )

        assert result == expected
        instance.update.assert_awaited_once_with(TARGET_ID, body, TENANT)

    @pytest.mark.asyncio
    async def test_update_target_raises_404_when_missing(self):
        from app.api.v1.target import update_target

        body = PerformanceTargetUpdate(target_value=2000.0)

        with patch("app.api.v1.target.TargetRepository") as MockRepo:
            instance = AsyncMock()
            instance.update.return_value = None
            MockRepo.return_value = instance

            with pytest.raises(HTTPException) as exc_info:
                await update_target(
                    target_id=TARGET_ID,
                    body=body,
                    db=AsyncMock(),
                    tenant_id=TENANT,
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------


class TestDashboardAPI:
    @pytest.mark.asyncio
    async def test_get_dashboard_returns_composite(self):
        from app.api.v1.dashboard import get_dashboard

        measurements = [_make_measurement(KPI_SPEC_ID, 900.0)]
        targets = [_make_target()]

        with patch("app.api.v1.dashboard.MeasurementRepository") as MockMeasRepo, \
             patch("app.api.v1.dashboard.TargetRepository") as MockTargetRepo:

            meas_instance = AsyncMock()
            meas_instance.list_with_filters.return_value = measurements
            MockMeasRepo.return_value = meas_instance

            target_instance = AsyncMock()
            target_instance.list_for_party.return_value = targets
            MockTargetRepo.return_value = target_instance

            result = await get_dashboard(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                period=date(2025, 1, 15),
            )

        assert isinstance(result, PerformanceDashboard)
        assert result.party_id == PARTY_ID
        assert result.period == date(2025, 1, 1)
        assert result.measurements == measurements
        assert result.targets == targets

    @pytest.mark.asyncio
    async def test_get_dashboard_period_normalised_to_first_of_month(self):
        from app.api.v1.dashboard import get_dashboard

        with patch("app.api.v1.dashboard.MeasurementRepository") as MockMeasRepo, \
             patch("app.api.v1.dashboard.TargetRepository") as MockTargetRepo:

            meas_instance = AsyncMock()
            meas_instance.list_with_filters.return_value = []
            MockMeasRepo.return_value = meas_instance

            target_instance = AsyncMock()
            target_instance.list_for_party.return_value = []
            MockTargetRepo.return_value = target_instance

            result = await get_dashboard(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                period=date(2025, 6, 20),
            )

        # period should be normalised to first day of month
        assert result.period == date(2025, 6, 1)

    @pytest.mark.asyncio
    async def test_get_dashboard_passes_period_start_to_repos(self):
        from app.api.v1.dashboard import get_dashboard

        with patch("app.api.v1.dashboard.MeasurementRepository") as MockMeasRepo, \
             patch("app.api.v1.dashboard.TargetRepository") as MockTargetRepo:

            meas_instance = AsyncMock()
            meas_instance.list_with_filters.return_value = []
            MockMeasRepo.return_value = meas_instance

            target_instance = AsyncMock()
            target_instance.list_for_party.return_value = []
            MockTargetRepo.return_value = target_instance

            await get_dashboard(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                period=date(2025, 3, 10),
            )

        expected_period = date(2025, 3, 1)
        meas_instance.list_with_filters.assert_awaited_once_with(
            tenant_id=TENANT,
            party_id=PARTY_ID,
            from_date=expected_period,
            to_date=expected_period,
        )
        target_instance.list_for_party.assert_awaited_once_with(
            party_id=PARTY_ID,
            tenant_id=TENANT,
            period=expected_period,
        )

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_contains_variance(self):
        from app.api.v1.dashboard import get_dashboard

        kpi_id = uuid.uuid4()
        measurements = [_make_measurement(kpi_id, 1200.0)]
        target = PerformanceTarget(
            id=uuid.uuid4(),
            party_id=PARTY_ID,
            kpi_spec_id=kpi_id,
            target_value=1000.0,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status=TargetStatus.ACTIVE,
            tenant_id=TENANT,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )

        with patch("app.api.v1.dashboard.MeasurementRepository") as MockMeasRepo, \
             patch("app.api.v1.dashboard.TargetRepository") as MockTargetRepo:

            meas_instance = AsyncMock()
            meas_instance.list_with_filters.return_value = measurements
            MockMeasRepo.return_value = meas_instance

            target_instance = AsyncMock()
            target_instance.list_for_party.return_value = [target]
            MockTargetRepo.return_value = target_instance

            result = await get_dashboard(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                period=date(2025, 1, 1),
            )

        entry = result.summary[str(kpi_id)]
        assert entry["achieved"] is True
        assert entry["variance_pct"] == 20.0

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_returns_empty_summary(self):
        from app.api.v1.dashboard import get_dashboard

        with patch("app.api.v1.dashboard.MeasurementRepository") as MockMeasRepo, \
             patch("app.api.v1.dashboard.TargetRepository") as MockTargetRepo:

            meas_instance = AsyncMock()
            meas_instance.list_with_filters.return_value = []
            MockMeasRepo.return_value = meas_instance

            target_instance = AsyncMock()
            target_instance.list_for_party.return_value = []
            MockTargetRepo.return_value = target_instance

            result = await get_dashboard(
                db=AsyncMock(),
                tenant_id=TENANT,
                party_id=PARTY_ID,
                period=date(2025, 1, 1),
            )

        assert result.summary == {}
        assert result.measurements == []
        assert result.targets == []


# ---------------------------------------------------------------------------
# Repository: additional branches
# ---------------------------------------------------------------------------


class TestIndicatorSpecRepositoryExtra:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_missing(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import IndicatorSpecRepository

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        repo = IndicatorSpecRepository(mock_db_session)
        result = await repo.get_by_id(uuid.uuid4(), sample_tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_returns_empty_list(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import IndicatorSpecRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = IndicatorSpecRepository(mock_db_session)
        result = await repo.list_all(sample_tenant_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_update_with_empty_patch_calls_get_by_id(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import IndicatorSpecRepository

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        repo = IndicatorSpecRepository(mock_db_session)
        spec_id = uuid.uuid4()
        # PerformanceIndicatorSpecUpdate with no fields → empty patch
        from app.domain.models import PerformanceIndicatorSpecUpdate
        result = await repo.update(spec_id, PerformanceIndicatorSpecUpdate(), sample_tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_with_patch_executes_update_then_get(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import IndicatorSpecRepository

        spec_id = uuid.uuid4()
        # patch select and update from sqlalchemy to avoid real SQLAlchemy models
        none_result = MagicMock()
        none_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = none_result

        from app.domain.models import PerformanceIndicatorSpecUpdate
        with patch("app.infrastructure.db.repository.update") as mock_update, \
             patch("app.infrastructure.db.repository.select") as mock_select:
            mock_update.return_value.where.return_value.values.return_value = MagicMock()
            mock_select.return_value.where.return_value = MagicMock()

            repo = IndicatorSpecRepository(mock_db_session)
            result = await repo.update(
                spec_id, PerformanceIndicatorSpecUpdate(name="New Name"), sample_tenant_id
            )

        # execute should be called twice: once for update, once for get_by_id
        assert mock_db_session.execute.await_count == 2
        assert result is None  # scalar_one_or_none returned None


class TestTargetRepositoryExtra:
    @pytest.mark.asyncio
    async def test_create_target_calls_add_flush_refresh(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        target_id = uuid.uuid4()
        orm_obj = MagicMock()
        orm_obj.id = target_id
        orm_obj.party_id = PARTY_ID
        orm_obj.kpi_spec_id = KPI_SPEC_ID
        orm_obj.target_value = 500.0
        orm_obj.period_start = date(2025, 1, 1)
        orm_obj.period_end = date(2025, 1, 31)
        orm_obj.status = TargetStatus.ACTIVE
        orm_obj.tenant_id = sample_tenant_id
        orm_obj.created_at = datetime(2025, 1, 1)
        orm_obj.updated_at = datetime(2025, 1, 1)

        expected = PerformanceTarget(
            id=target_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            target_value=500.0,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            status=TargetStatus.ACTIVE,
            tenant_id=sample_tenant_id,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )

        with patch(
            "app.infrastructure.db.repository.PerformanceTargetDB",
            return_value=orm_obj,
        ), patch.object(PerformanceTarget, "model_validate", return_value=expected):
            repo = TargetRepository(mock_db_session)
            from app.domain.models import PerformanceTargetCreate
            create_data = PerformanceTargetCreate(
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                target_value=500.0,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
            )
            result = await repo.create(create_data, sample_tenant_id)

        assert result.target_value == 500.0
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_for_party_without_period(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = TargetRepository(mock_db_session)
        result = await repo.list_for_party(party_id=PARTY_ID, tenant_id=sample_tenant_id)
        assert result == []
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_for_party_with_period(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = TargetRepository(mock_db_session)
        result = await repo.list_for_party(
            party_id=PARTY_ID,
            tenant_id=sample_tenant_id,
            period=date(2025, 1, 1),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_update_target_with_empty_patch_calls_get_by_id(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        repo = TargetRepository(mock_db_session)
        from app.domain.models import PerformanceTargetUpdate
        result = await repo.update(TARGET_ID, PerformanceTargetUpdate(), sample_tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_target_with_values_executes_update(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        # First call for update execute, second for get_by_id
        result_mock_empty = MagicMock()
        result_mock_empty.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock_empty

        repo = TargetRepository(mock_db_session)
        from app.domain.models import PerformanceTargetUpdate
        await repo.update(TARGET_ID, PerformanceTargetUpdate(target_value=999.0), sample_tenant_id)
        # execute should be called twice: once for update, once for get_by_id
        assert mock_db_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_get_active_for_party_and_spec(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import TargetRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = TargetRepository(mock_db_session)
        result = await repo.get_active_for_party_and_spec(
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            period=date(2025, 1, 1),
            tenant_id=sample_tenant_id,
        )
        assert result == []
        mock_db_session.execute.assert_awaited_once()


class TestMeasurementRepositoryExtra:
    @pytest.mark.asyncio
    async def test_list_with_filters_all_none(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = MeasurementRepository(mock_db_session)
        result = await repo.list_with_filters(tenant_id=sample_tenant_id)
        assert result == []
        mock_db_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_with_filters_all_set(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_db_session.execute.return_value = result_mock

        repo = MeasurementRepository(mock_db_session)
        result = await repo.list_with_filters(
            tenant_id=sample_tenant_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_when_found(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        meas_id = uuid.uuid4()
        existing = PerformanceMeasurement(
            id=meas_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            period=date(2025, 1, 1),
            measured_value=100.0,
            source_event_ids=["evt-old"],
            tenant_id=sample_tenant_id,
            created_at=datetime(2025, 1, 1),
        )
        updated = PerformanceMeasurement(
            id=meas_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            period=date(2025, 1, 1),
            measured_value=150.0,
            source_event_ids=["evt-old", "evt-new"],
            tenant_id=sample_tenant_id,
            created_at=datetime(2025, 1, 1),
        )

        # Use an ORM-like object for _get_by_id_raw to validate
        orm_raw = MagicMock()

        repo = MeasurementRepository(mock_db_session)
        with patch.object(repo, "_get_by_party_spec_period", return_value=existing), \
             patch.object(repo, "_get_by_id_raw", return_value=orm_raw), \
             patch.object(PerformanceMeasurement, "model_validate", return_value=updated), \
             patch("app.infrastructure.db.repository.update") as mock_update:
            mock_update.return_value.where.return_value.values.return_value = MagicMock()

            result = await repo.upsert(
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                period=date(2025, 1, 1),
                measured_value=50.0,
                source_event_id="evt-new",
                tenant_id=sample_tenant_id,
            )

        assert result.measured_value == 150.0
        mock_db_session.execute.assert_awaited_once()  # only the update execute

    @pytest.mark.asyncio
    async def test_upsert_creates_new_when_not_existing(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        meas_id = uuid.uuid4()
        expected = PerformanceMeasurement(
            id=meas_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            period=date(2025, 1, 1),
            measured_value=50.0,
            source_event_ids=["evt-new"],
            tenant_id=sample_tenant_id,
            created_at=datetime(2025, 1, 1),
        )

        # Patch the private helper so it returns None (no existing record),
        # and patch model_validate to return our expected Pydantic model.
        repo = MeasurementRepository(mock_db_session)
        with patch.object(repo, "_get_by_party_spec_period", return_value=None), \
             patch.object(PerformanceMeasurement, "model_validate", return_value=expected):
            result = await repo.upsert(
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                period=date(2025, 1, 1),
                measured_value=50.0,
                source_event_id="evt-new",
                tenant_id=sample_tenant_id,
            )

        assert result.measured_value == 50.0
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_party_spec_period_returns_none_when_missing(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = result_mock

        with patch("app.infrastructure.db.repository.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            repo = MeasurementRepository(mock_db_session)
            result = await repo._get_by_party_spec_period(
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                period=date(2025, 1, 1),
                tenant_id=sample_tenant_id,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_party_spec_period_returns_model_when_found(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        meas_id = uuid.uuid4()
        expected = PerformanceMeasurement(
            id=meas_id,
            party_id=PARTY_ID,
            kpi_spec_id=KPI_SPEC_ID,
            period=date(2025, 1, 1),
            measured_value=75.0,
            source_event_ids=["evt-x"],
            tenant_id=sample_tenant_id,
            created_at=datetime(2025, 1, 1),
        )
        orm_row = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm_row
        mock_db_session.execute.return_value = result_mock

        with patch("app.infrastructure.db.repository.select") as mock_select, \
             patch.object(PerformanceMeasurement, "model_validate", return_value=expected):
            mock_select.return_value.where.return_value = MagicMock()
            repo = MeasurementRepository(mock_db_session)
            result = await repo._get_by_party_spec_period(
                party_id=PARTY_ID,
                kpi_spec_id=KPI_SPEC_ID,
                period=date(2025, 1, 1),
                tenant_id=sample_tenant_id,
            )

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_by_id_raw_returns_result(self, mock_db_session, sample_tenant_id):
        from app.infrastructure.db.repository import MeasurementRepository

        orm_row = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm_row
        mock_db_session.execute.return_value = result_mock

        with patch("app.infrastructure.db.repository.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            repo = MeasurementRepository(mock_db_session)
            result = await repo._get_by_id_raw(uuid.uuid4())

        assert result is orm_row
