import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_kafka_producer():
    producer = AsyncMock()
    producer.send = AsyncMock()
    return producer


@pytest.fixture
def sample_tenant_id():
    return "tenant-test-001"
