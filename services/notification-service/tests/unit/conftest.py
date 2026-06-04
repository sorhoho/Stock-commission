"""Shared fixtures for notification-service unit tests.

No database, no real network — every external integration (SMTP, SMS HTTP
gateway, Kafka) is mocked.  Tests rely on ``asyncio_mode = "auto"`` configured
in pyproject.toml [tool.pytest.ini_options].
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_email_client() -> AsyncMock:
    """AsyncMock standing in for SmtpClient — send_email returns a message-id."""
    client = AsyncMock()
    client.send_email = AsyncMock(return_value="msg-email-1")
    return client


@pytest.fixture
def mock_sms_client() -> AsyncMock:
    """AsyncMock standing in for SmsClient — send_sms returns a message-id."""
    client = AsyncMock()
    client.send_sms = AsyncMock(return_value="msg-sms-1")
    return client
