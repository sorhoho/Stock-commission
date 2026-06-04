"""Unit tests for stock-query-service API handlers and domain models."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.domain.models import StockAvailability, StockQueryResult
from telco_common.exceptions import NotFoundException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT = "tenant-abc"
PRODUCT_ID = uuid.uuid4()
LOCATION_ID = uuid.uuid4()


def _make_availability_dict(
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    available: int = 100,
    reserved: int = 0,
) -> dict:
    return {
        "product_id": str(product_id or PRODUCT_ID),
        "product_name": "SIM Card",
        "location_id": str(location_id or LOCATION_ID),
        "location_type": "WAREHOUSE",
        "available_quantity": available,
        "reserved_quantity": reserved,
        "last_updated": "2025-01-15T10:00:00+00:00",
        "tenant_id": TENANT,
    }


def _make_stock_availability(
    product_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    available: int = 100,
    reserved: int = 0,
) -> StockAvailability:
    return StockAvailability(
        product_id=product_id or PRODUCT_ID,
        product_name="SIM Card",
        location_id=location_id or LOCATION_ID,
        location_type="WAREHOUSE",
        available_quantity=available,
        reserved_quantity=reserved,
        last_updated="2025-01-15T10:00:00+00:00",
        tenant_id=TENANT,
    )


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


class TestStockAvailabilityModel:
    def test_net_quantity_is_available_minus_reserved(self):
        avail = _make_stock_availability(available=100, reserved=30)
        assert avail.net_quantity == 70

    def test_net_quantity_floors_at_zero(self):
        avail = _make_stock_availability(available=10, reserved=20)
        assert avail.net_quantity == 0

    def test_net_quantity_zero_reserved(self):
        avail = _make_stock_availability(available=50, reserved=0)
        assert avail.net_quantity == 50

    def test_model_validate_from_dict(self):
        raw = _make_availability_dict()
        avail = StockAvailability.model_validate(raw)
        assert avail.product_id == PRODUCT_ID
        assert avail.tenant_id == TENANT
        assert avail.available_quantity == 100

    def test_stock_query_result_total(self):
        items = [_make_stock_availability(), _make_stock_availability()]
        result = StockQueryResult(items=items, total=len(items))
        assert result.total == 2
        assert len(result.items) == 2

    def test_stock_query_result_empty(self):
        result = StockQueryResult(items=[], total=0)
        assert result.total == 0

    def test_stock_availability_from_attributes(self):
        """Verify from_attributes=True works (covers model_config line)."""
        raw = _make_availability_dict()
        avail = StockAvailability.model_validate(raw)
        assert isinstance(avail, StockAvailability)


# ---------------------------------------------------------------------------
# API handler tests: query_stock_availability
# ---------------------------------------------------------------------------


class TestQueryStockAvailabilityAPI:
    @pytest.mark.asyncio
    async def test_query_returns_all_items_no_filters(self):
        from app.api.v1.stock_query import query_stock_availability

        raw_items = [_make_availability_dict()]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=None,
            location_id=None,
            min_quantity=None,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert isinstance(result, StockQueryResult)
        assert result.total == 1
        assert len(result.items) == 1
        mock_read_model.query.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=None,
            location_id=None,
            min_quantity=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_product_id_filter(self):
        from app.api.v1.stock_query import query_stock_availability

        raw_items = [_make_availability_dict()]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=PRODUCT_ID,
            location_id=None,
            min_quantity=None,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 1
        mock_read_model.query.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=str(PRODUCT_ID),
            location_id=None,
            min_quantity=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_location_id_filter(self):
        from app.api.v1.stock_query import query_stock_availability

        raw_items = [_make_availability_dict()]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=None,
            location_id=LOCATION_ID,
            min_quantity=None,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 1
        mock_read_model.query.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=None,
            location_id=str(LOCATION_ID),
            min_quantity=None,
        )

    @pytest.mark.asyncio
    async def test_query_with_min_quantity_filter(self):
        from app.api.v1.stock_query import query_stock_availability

        raw_items = [_make_availability_dict(available=200)]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=None,
            location_id=None,
            min_quantity=50,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 1
        mock_read_model.query.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=None,
            location_id=None,
            min_quantity=50,
        )

    @pytest.mark.asyncio
    async def test_query_with_all_filters(self):
        from app.api.v1.stock_query import query_stock_availability

        raw_items = [_make_availability_dict()]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=PRODUCT_ID,
            location_id=LOCATION_ID,
            min_quantity=10,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 1
        mock_read_model.query.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=str(PRODUCT_ID),
            location_id=str(LOCATION_ID),
            min_quantity=10,
        )

    @pytest.mark.asyncio
    async def test_query_returns_empty_list(self):
        from app.api.v1.stock_query import query_stock_availability

        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = []

        result = await query_stock_availability(
            product_id=None,
            location_id=None,
            min_quantity=None,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_query_returns_multiple_items(self):
        from app.api.v1.stock_query import query_stock_availability

        other_product = uuid.uuid4()
        raw_items = [
            _make_availability_dict(),
            _make_availability_dict(product_id=other_product, available=50),
        ]
        mock_read_model = AsyncMock()
        mock_read_model.query.return_value = raw_items

        result = await query_stock_availability(
            product_id=None,
            location_id=None,
            min_quantity=None,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert result.total == 2
        assert len(result.items) == 2


# ---------------------------------------------------------------------------
# API handler tests: get_stock_availability
# ---------------------------------------------------------------------------


class TestGetStockAvailabilityAPI:
    @pytest.mark.asyncio
    async def test_get_returns_availability_when_found(self):
        from app.api.v1.stock_query import get_stock_availability

        raw = _make_availability_dict()
        mock_read_model = AsyncMock()
        mock_read_model.get_availability.return_value = raw

        result = await get_stock_availability(
            product_id=PRODUCT_ID,
            location_id=LOCATION_ID,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        assert isinstance(result, StockAvailability)
        assert result.product_id == PRODUCT_ID
        assert result.location_id == LOCATION_ID
        mock_read_model.get_availability.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=str(PRODUCT_ID),
            location_id=str(LOCATION_ID),
        )

    @pytest.mark.asyncio
    async def test_get_raises_404_when_not_found(self):
        from app.api.v1.stock_query import get_stock_availability

        mock_read_model = AsyncMock()
        mock_read_model.get_availability.return_value = None

        with pytest.raises(NotFoundException) as exc_info:
            await get_stock_availability(
                product_id=PRODUCT_ID,
                location_id=LOCATION_ID,
                tenant_id=TENANT,
                read_model=mock_read_model,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_passes_correct_string_ids(self):
        from app.api.v1.stock_query import get_stock_availability

        raw = _make_availability_dict()
        mock_read_model = AsyncMock()
        mock_read_model.get_availability.return_value = raw

        await get_stock_availability(
            product_id=PRODUCT_ID,
            location_id=LOCATION_ID,
            tenant_id=TENANT,
            read_model=mock_read_model,
        )

        mock_read_model.get_availability.assert_awaited_once_with(
            tenant_id=TENANT,
            product_id=str(PRODUCT_ID),
            location_id=str(LOCATION_ID),
        )


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


class TestStockQueryRouter:
    def test_router_has_correct_prefix(self):
        from app.api.v1.router import router
        assert router.prefix == "/api/v1/inventory"

    def test_stock_query_router_has_routes(self):
        from app.api.v1.router import router
        assert len(router.routes) > 0


# ---------------------------------------------------------------------------
# Dependencies tests
# ---------------------------------------------------------------------------


class TestDependencies:
    def test_get_stock_read_model_returns_model(self):
        from app.dependencies import get_stock_read_model

        mock_model = MagicMock()
        request = MagicMock()
        request.app.state.stock_read_model = mock_model

        result = get_stock_read_model(request)
        assert result is mock_model

    def test_get_stock_read_model_raises_503_when_missing(self):
        from app.dependencies import get_stock_read_model

        request = MagicMock()
        request.app.state.stock_read_model = None

        with pytest.raises(HTTPException) as exc_info:
            get_stock_read_model(request)
        assert exc_info.value.status_code == 503

    def test_get_redis_client_returns_client(self):
        from app.dependencies import get_redis_client

        mock_client = MagicMock()
        request = MagicMock()
        request.app.state.redis_client = mock_client

        result = get_redis_client(request)
        assert result is mock_client

    def test_get_redis_client_raises_503_when_missing(self):
        from app.dependencies import get_redis_client

        request = MagicMock()
        request.app.state.redis_client = None

        with pytest.raises(HTTPException) as exc_info:
            get_redis_client(request)
        assert exc_info.value.status_code == 503

    def test_get_current_tenant_id_returns_tenant(self):
        from app.dependencies import get_current_tenant_id

        request = MagicMock()
        request.state.tenant_id = "tenant-x"

        result = get_current_tenant_id(request)
        assert result == "tenant-x"

    def test_get_current_tenant_id_raises_400_when_missing(self):
        from app.dependencies import get_current_tenant_id

        request = MagicMock()
        request.state.tenant_id = ""

        with pytest.raises(HTTPException) as exc_info:
            get_current_tenant_id(request)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestConfig:
    def test_settings_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.service_name == "stock-query-service"
        assert "redis" in s.redis_url
        assert s.redis_key_ttl_seconds == 86400
        assert "kafka" in s.kafka_bootstrap_servers
        assert s.kafka_consumer_group_id == "stock-query-service"
        assert s.debug is False

    def test_settings_singleton_importable(self):
        from app.config import settings
        assert settings is not None
        assert settings.service_name == "stock-query-service"


# ---------------------------------------------------------------------------
# InventoryConsumer tests
# ---------------------------------------------------------------------------


class TestInventoryConsumer:
    def test_init_stores_read_model(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer

        mock_read_model = MagicMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer") as MockKafka:
            MockKafka.return_value = MagicMock()
            consumer = InventoryConsumer(
                bootstrap_servers="kafka:9092",
                group_id="test-group",
                read_model=mock_read_model,
            )

        assert consumer._read_model is mock_read_model
        assert consumer._started is False

    @pytest.mark.asyncio
    async def test_stop_calls_consumer_stop(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer

        mock_read_model = MagicMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        await consumer.stop()
        mock_kafka.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_routes_adjustment(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer
        from telco_common.events.cloudevents import Topics

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        event = {
            "type": Topics.INVENTORY_STOCK_ADJUSTED,
            "id": "evt-001",
            "tenantid": TENANT,
            "data": {"product_id": str(PRODUCT_ID)},
        }
        await consumer._dispatch(event)
        mock_read_model.update_from_adjustment.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_routes_transfer(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer
        from telco_common.events.cloudevents import Topics

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        event = {
            "type": Topics.INVENTORY_STOCK_TRANSFERRED,
            "id": "evt-002",
            "tenantid": TENANT,
            "data": {"product_id": str(PRODUCT_ID)},
        }
        await consumer._dispatch(event)
        mock_read_model.update_from_transfer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_skips_unknown_event_type(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        event = {"type": "unknown.event", "id": "evt-003", "tenantid": TENANT, "data": {}}
        await consumer._dispatch(event)

        mock_read_model.update_from_adjustment.assert_not_awaited()
        mock_read_model.update_from_transfer.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_injects_tenant_id_from_envelope(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer
        from telco_common.events.cloudevents import Topics

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        event = {
            "type": Topics.INVENTORY_STOCK_ADJUSTED,
            "id": "evt-004",
            "tenantid": "envelope-tenant",
            "data": {},  # no tenant_id in data
        }
        await consumer._dispatch(event)

        # update_from_adjustment should be called with tenant_id injected
        call_args = mock_read_model.update_from_adjustment.await_args
        data_arg = call_args[0][0]
        assert data_arg.get("tenant_id") == "envelope-tenant"

    @pytest.mark.asyncio
    async def test_run_starts_and_consumes(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        await consumer.run()

        mock_kafka.start.assert_awaited_once()
        mock_kafka.consume.assert_awaited_once()
        assert consumer._started is True

    @pytest.mark.asyncio
    async def test_dispatch_does_not_override_existing_tenant_id(self):
        from app.infrastructure.kafka.consumers.inventory_consumer import InventoryConsumer
        from telco_common.events.cloudevents import Topics

        mock_read_model = AsyncMock()
        mock_kafka = AsyncMock()
        with patch("app.infrastructure.kafka.consumers.inventory_consumer.KafkaConsumer", return_value=mock_kafka):
            consumer = InventoryConsumer("kafka:9092", "grp", mock_read_model)

        event = {
            "type": Topics.INVENTORY_STOCK_ADJUSTED,
            "id": "evt-005",
            "tenantid": "envelope-tenant",
            "data": {"tenant_id": "data-tenant"},  # already has tenant_id
        }
        await consumer._dispatch(event)

        call_args = mock_read_model.update_from_adjustment.await_args
        data_arg = call_args[0][0]
        # original data tenant_id should be preserved
        assert data_arg.get("tenant_id") == "data-tenant"


# ---------------------------------------------------------------------------
# Main app tests
# ---------------------------------------------------------------------------


class TestMainApp:
    def test_create_app_returns_fastapi_instance(self):
        from fastapi import FastAPI
        from app.main import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_health_endpoint(self):
        from app.main import create_app

        app = create_app()
        routes = {r.path for r in app.routes}
        assert "/health" in routes

    def test_get_redis_client_raises_when_not_init(self):
        import app.main as main_mod

        original = main_mod._redis_client
        main_mod._redis_client = None
        try:
            with pytest.raises(RuntimeError, match="not initialised"):
                main_mod.get_redis_client()
        finally:
            main_mod._redis_client = original

    def test_get_stock_read_model_raises_when_not_init(self):
        import app.main as main_mod

        original = main_mod._stock_read_model
        main_mod._stock_read_model = None
        try:
            with pytest.raises(RuntimeError, match="not initialised"):
                main_mod.get_stock_read_model()
        finally:
            main_mod._stock_read_model = original

    def test_get_redis_client_returns_client_when_set(self):
        import app.main as main_mod

        mock_client = MagicMock()
        original = main_mod._redis_client
        main_mod._redis_client = mock_client
        try:
            result = main_mod.get_redis_client()
            assert result is mock_client
        finally:
            main_mod._redis_client = original

    def test_get_stock_read_model_returns_model_when_set(self):
        import app.main as main_mod

        mock_model = MagicMock()
        original = main_mod._stock_read_model
        main_mod._stock_read_model = mock_model
        try:
            result = main_mod.get_stock_read_model()
            assert result is mock_model
        finally:
            main_mod._stock_read_model = original
