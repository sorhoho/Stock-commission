"""Shared pytest fixtures for performance-service tests."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.models import (
    IndicatorType,
    MeasurementInterval,
    TargetStatus,
)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Return a mock async DB session."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_kafka_producer() -> AsyncMock:
    """Return a mock Kafka producer."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    return producer


@pytest.fixture
def sample_tenant_id() -> str:
    return "tenant-abc"


@pytest.fixture
def sample_indicator_spec_data() -> dict:
    return {
        "name": "MONTHLY_SELL_OUT_REVENUE",
        "description": "Monthly sell-out revenue",
        "unit_of_measure": "USD",
        "indicator_type": IndicatorType.GAUGE,
        "measurement_interval": MeasurementInterval.MONTHLY,
    }
