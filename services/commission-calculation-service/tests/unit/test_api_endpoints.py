"""Unit tests for commission-calculation-service API handler functions.

Tests call the async handler functions directly with mocked repos and a fake
token, avoiding HTTP/lifespan/DB setup.  These verify the handler logic:
correct repo delegation, NotFoundException on miss, ConflictException on
already-confirmed statement, etc.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.domain.models import (
    CommissionEvent,
    CommissionEventStatus,
    CommissionStatement,
    CommissionStatementStatus,
)
from telco_common.auth.jwt_bearer import TokenPayload
from telco_common.exceptions import ConflictException, NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"
PARTY = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _fake_token(tenant_id: str = TENANT) -> TokenPayload:
    return TokenPayload(sub="tester", tenant_id=tenant_id, scope="commission:read")


def _make_event(**overrides) -> CommissionEvent:
    defaults = dict(
        id=uuid.uuid4(),
        source_transaction_id=uuid.uuid4(),
        party_id=PARTY,
        agreement_id=uuid.uuid4(),
        rule_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity=5,
        base_amount=50.0,
        commission_amount=4.0,
        currency="USD",
        calculation_date=datetime.now(UTC),
        status=CommissionEventStatus.CALCULATED,
        tenant_id=TENANT,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return CommissionEvent(**defaults)


def _make_statement(**overrides) -> CommissionStatement:
    defaults = dict(
        id=uuid.uuid4(),
        party_id=PARTY,
        period_year=2026,
        period_month=1,
        total_commission=100.0,
        currency="USD",
        line_items_count=5,
        status=CommissionStatementStatus.DRAFT,
        confirmed_at=None,
        tenant_id=TENANT,
    )
    defaults.update(overrides)
    return CommissionStatement(**defaults)


# ── commission_event handlers ─────────────────────────────────────────────────


async def test_list_commission_events_returns_paginated():
    from app.api.v1.commission_event import list_commission_events

    ev = _make_event()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_event.CommissionEventRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = ([ev], 1)
        MockRepo.return_value = instance

        result = await list_commission_events(
            party_id=None, from_date=None, to_date=None, status=None,
            page=1, size=20, db=mock_db, token=token,
        )

    assert result["total"] == 1
    assert result["page"] == 1
    assert result["size"] == 20
    assert len(result["items"]) == 1
    instance.list_with_filters.assert_awaited_once_with(
        tenant_id=TENANT, party_id=None, from_date=None, to_date=None,
        status=None, page=1, size=20,
    )


async def test_list_commission_events_with_party_filter():
    from app.api.v1.commission_event import list_commission_events

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_event.CommissionEventRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = ([], 0)
        MockRepo.return_value = instance

        await list_commission_events(
            party_id=PARTY, from_date=None, to_date=None, status=None,
            page=1, size=20, db=mock_db, token=token,
        )

    instance.list_with_filters.assert_awaited_once()
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["party_id"] == PARTY
    assert kwargs["tenant_id"] == TENANT


async def test_get_commission_event_found():
    from app.api.v1.commission_event import get_commission_event

    ev = _make_event()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_event.CommissionEventRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = ev
        MockRepo.return_value = instance

        result = await get_commission_event(event_id=ev.id, db=mock_db, token=token)

    assert result.id == ev.id
    instance.get_by_id.assert_awaited_once_with(ev.id, TENANT)


async def test_get_commission_event_not_found():
    from app.api.v1.commission_event import get_commission_event

    mock_db = AsyncMock()
    token = _fake_token()
    event_id = uuid.uuid4()

    with patch("app.api.v1.commission_event.CommissionEventRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_commission_event(event_id=event_id, db=mock_db, token=token)


async def test_trigger_recalculate_returns_accepted():
    from app.api.v1.commission_event import trigger_recalculate

    token = _fake_token()
    body = {"party_id": str(PARTY), "year": 2026, "month": 1}

    result = await trigger_recalculate(body=body, _token=token)
    assert result["status"] == "accepted"
    assert result["params"] == body


# ── commission_statement handlers ─────────────────────────────────────────────


async def test_list_statements_empty():
    from app.api.v1.commission_statement import list_statements

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = ([], 0)
        MockRepo.return_value = instance

        result = await list_statements(party_id=None, year=None, month=None, db=mock_db, token=token)

    assert result == []
    instance.list_with_filters.assert_awaited_once_with(
        tenant_id=TENANT, party_id=None, year=None, month=None,
    )


async def test_list_statements_with_filters():
    from app.api.v1.commission_statement import list_statements

    stmt = _make_statement()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = ([stmt], 1)
        MockRepo.return_value = instance

        result = await list_statements(party_id=PARTY, year=2026, month=1, db=mock_db, token=token)

    assert len(result) == 1
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["party_id"] == PARTY
    assert kwargs["year"] == 2026
    assert kwargs["month"] == 1


async def test_get_statement_found():
    from app.api.v1.commission_statement import get_statement

    stmt = _make_statement()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = stmt
        MockRepo.return_value = instance

        result = await get_statement(statement_id=stmt.id, db=mock_db, token=token)

    assert result.id == stmt.id
    instance.get_by_id.assert_awaited_once_with(stmt.id, TENANT)


async def test_get_statement_not_found():
    from app.api.v1.commission_statement import get_statement

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_statement(statement_id=uuid.uuid4(), db=mock_db, token=token)


async def test_confirm_statement_draft():
    from app.api.v1.commission_statement import confirm_statement

    stmt = _make_statement(status=CommissionStatementStatus.DRAFT)
    confirmed = _make_statement(status=CommissionStatementStatus.CONFIRMED, confirmed_at=datetime.now(UTC))
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = stmt
        instance.confirm.return_value = confirmed
        MockRepo.return_value = instance

        result = await confirm_statement(statement_id=stmt.id, db=mock_db, token=token)

    assert result.status == CommissionStatementStatus.CONFIRMED
    instance.confirm.assert_awaited_once_with(str(stmt.id))


async def test_confirm_statement_not_draft_raises_conflict():
    from app.api.v1.commission_statement import confirm_statement

    stmt = _make_statement(status=CommissionStatementStatus.CONFIRMED)
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = stmt
        MockRepo.return_value = instance

        with pytest.raises(ConflictException):
            await confirm_statement(statement_id=stmt.id, db=mock_db, token=token)


async def test_confirm_statement_not_found():
    from app.api.v1.commission_statement import confirm_statement

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await confirm_statement(statement_id=uuid.uuid4(), db=mock_db, token=token)


async def test_dispute_statement_found():
    from app.api.v1.commission_statement import dispute_statement

    stmt = _make_statement()
    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = stmt
        MockRepo.return_value = instance

        result = await dispute_statement(
            statement_id=stmt.id,
            body={"reason": "Wrong rate"},
            db=mock_db,
            token=token,
        )

    assert result["status"] == "dispute_received"
    assert result["reason"] == "Wrong rate"
    assert result["statement_id"] == str(stmt.id)


async def test_dispute_statement_not_found():
    from app.api.v1.commission_statement import dispute_statement

    mock_db = AsyncMock()
    token = _fake_token()

    with patch("app.api.v1.commission_statement.CommissionStatementRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await dispute_statement(
                statement_id=uuid.uuid4(),
                body={"reason": "Disputed"},
                db=mock_db,
                token=token,
            )
