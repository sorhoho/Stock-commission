"""Unit tests for audit-service API handler functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.db.models import AuditLog
from telco_common.auth.jwt_bearer import TokenPayload

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"


def _fake_token(tenant_id: str = TENANT) -> TokenPayload:
    return TokenPayload(sub="tester", tenant_id=tenant_id, scope="audit:read")


def _make_log(tenant_id: str = TENANT) -> AuditLog:
    return AuditLog(
        id=uuid.uuid4(),
        event_id=f"evt-{uuid.uuid4()}",
        event_type="telco.sales.sellout.completed",
        event_source="sell-out-service",
        tenant_id=tenant_id,
        correlation_id="corr-1",
        event_time="2026-01-15T10:00:00+00:00",
        payload={"foo": "bar"},
        received_at=datetime.now(UTC),
    )


async def test_list_audit_logs_empty():
    from app.api.v1.audit_log import list_audit_logs

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.audit_log.AuditLogRepository") as MockRepo:
        instance = AsyncMock()
        instance.query.return_value = ([], 0)
        MockRepo.return_value = instance

        result = await list_audit_logs(
            event_type=None, from_date=None, to_date=None,
            page=1, size=50, db=mock_db, token=token,
        )

    assert result["total"] == 0
    assert result["items"] == []
    instance.query.assert_awaited_once_with(TENANT, event_type=None, from_date=None, to_date=None, page=1, size=50)


async def test_list_audit_logs_returns_items():
    from app.api.v1.audit_log import list_audit_logs

    log = _make_log()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.audit_log.AuditLogRepository") as MockRepo:
        instance = AsyncMock()
        instance.query.return_value = ([log], 1)
        MockRepo.return_value = instance

        result = await list_audit_logs(
            event_type=None, from_date=None, to_date=None,
            page=1, size=50, db=mock_db, token=token,
        )

    assert result["total"] == 1
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["event_type"] == "telco.sales.sellout.completed"
    assert item["tenant_id"] == TENANT
    assert "id" in item


async def test_list_audit_logs_with_event_type_filter():
    from app.api.v1.audit_log import list_audit_logs

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.audit_log.AuditLogRepository") as MockRepo:
        instance = AsyncMock()
        instance.query.return_value = ([], 0)
        MockRepo.return_value = instance

        await list_audit_logs(
            event_type="telco.sales.sellout.completed",
            from_date="2026-01-01", to_date="2026-01-31",
            page=2, size=25, db=mock_db, token=token,
        )

    instance.query.assert_awaited_once_with(
        TENANT,
        event_type="telco.sales.sellout.completed",
        from_date="2026-01-01",
        to_date="2026-01-31",
        page=2,
        size=25,
    )


async def test_list_audit_logs_tenant_isolation():
    from app.api.v1.audit_log import list_audit_logs

    mock_db = AsyncMock()
    other_tenant = "tenant-other"
    token = _fake_token(tenant_id=other_tenant)

    with patch("app.api.v1.audit_log.AuditLogRepository") as MockRepo:
        instance = AsyncMock()
        instance.query.return_value = ([], 0)
        MockRepo.return_value = instance

        await list_audit_logs(
            event_type=None, from_date=None, to_date=None,
            page=1, size=50, db=mock_db, token=token,
        )

    called_tenant = instance.query.call_args[0][0]
    assert called_tenant == other_tenant


def test_config_import():
    from app.config import settings
    assert settings.service_name is not None


def test_dependencies_import():
    import app.dependencies
    assert hasattr(app.dependencies, "get_db")


def test_router_import():
    from app.api.v1.router import router
    assert router.prefix == "/api/v1/audit"


async def test_get_db_commit_path():
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.async_session_factory", return_value=mock_ctx):
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
        # Resume the generator to trigger commit after yield
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    mock_session.commit.assert_awaited_once()


async def test_get_db_rollback_on_exception():
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.async_session_factory", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(ValueError):
            await gen.athrow(ValueError("oops"))

    mock_session.rollback.assert_awaited_once()


async def test_health_endpoint():
    from app.main import health
    result = await health()
    assert result["status"] == "ok"
    assert "service" in result


def test_main_app_created():
    from app.main import app
    assert app.title == "Audit Service"
