"""Unit tests for party-service API handler functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models import (
    Party,
    PartyCharacteristic,
    PartyCharacteristicCreate,
    PartyCreate,
    PartyRole,
    PartyStatus,
    PartyType,
    PartyUpdate,
)
from telco_common.exceptions import NotFoundException

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"


def _make_party(**overrides) -> Party:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        href="/api/v1/party/" + str(uuid.uuid4()),
        party_type=PartyType.INDIVIDUAL,
        role=PartyRole.DEALER,
        name="Test Dealer",
        status=PartyStatus.ACTIVE,
        tenant_id=TENANT,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Party(**defaults)


# ── list_parties ──────────────────────────────────────────────────────────────


async def test_list_parties_empty():
    from app.api.v1.party import list_parties

    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = []
        MockRepo.return_value = instance

        result = await list_parties(
            role=None, status=None, parent_party_id=None,
            page=1, size=20, tenant_id=TENANT, db=mock_db,
        )

    assert result == []
    instance.list_with_filters.assert_awaited_once_with(
        tenant_id=TENANT, role=None, status=None, parent_party_id=None,
        page=1, size=20,
    )


async def test_list_parties_with_filters():
    from app.api.v1.party import list_parties

    party = _make_party()
    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.list_with_filters.return_value = [party]
        MockRepo.return_value = instance

        with patch("app.api.v1.party.Party") as MockModel:
            MockModel.model_validate.return_value = party

            result = await list_parties(
                role=PartyRole.DEALER, status=PartyStatus.ACTIVE, parent_party_id=None,
                page=1, size=20, tenant_id=TENANT, db=mock_db,
            )

    assert len(result) == 1
    kwargs = instance.list_with_filters.call_args.kwargs
    assert kwargs["role"] == PartyRole.DEALER
    assert kwargs["status"] == PartyStatus.ACTIVE


# ── get_party ─────────────────────────────────────────────────────────────────


async def test_get_party_found():
    from app.api.v1.party import get_party

    party = _make_party()
    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = party
        MockRepo.return_value = instance

        with patch("app.api.v1.party.Party") as MockModel:
            MockModel.model_validate.return_value = party
            result = await get_party(party_id=party.id, tenant_id=TENANT, db=mock_db)

    assert result.id == party.id


async def test_get_party_not_found():
    from app.api.v1.party import get_party

    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.get_by_id.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await get_party(party_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


# ── create_party ──────────────────────────────────────────────────────────────


async def test_create_party_delegates_to_service():
    from app.api.v1.party import create_party

    party = _make_party()
    mock_db = AsyncMock()
    mock_kafka = AsyncMock()
    body = PartyCreate(
        party_type=PartyType.INDIVIDUAL,
        role=PartyRole.DEALER,
        name="New Dealer",
    )

    with patch("app.api.v1.party.services") as mock_svc_mod:
        mock_svc_mod.onboard_party = AsyncMock(return_value=party)

        with patch("app.api.v1.party.Party") as MockModel:
            MockModel.model_validate.return_value = party

            result = await create_party(
                body=body, region="North", tier="Gold",
                tenant_id=TENANT, correlation_id="corr-1",
                db=mock_db, kafka_producer=mock_kafka,
            )

    assert result.id == party.id
    mock_svc_mod.onboard_party.assert_awaited_once()


# ── update_party ──────────────────────────────────────────────────────────────


async def test_update_party_found():
    from app.api.v1.party import update_party

    party = _make_party(name="Updated Name")
    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.update.return_value = party
        MockRepo.return_value = instance

        with patch("app.api.v1.party.Party") as MockModel:
            MockModel.model_validate.return_value = party

            result = await update_party(
                party_id=party.id, body=PartyUpdate(name="Updated Name"),
                tenant_id=TENANT, db=mock_db,
            )

    assert result.name == "Updated Name"


async def test_update_party_not_found():
    from app.api.v1.party import update_party

    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.update.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await update_party(
                party_id=uuid.uuid4(), body=PartyUpdate(name="X"),
                tenant_id=TENANT, db=mock_db,
            )


# ── delete_party ──────────────────────────────────────────────────────────────


async def test_delete_party_found():
    from app.api.v1.party import delete_party

    party = _make_party()
    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.soft_delete.return_value = party
        MockRepo.return_value = instance

        result = await delete_party(party_id=party.id, tenant_id=TENANT, db=mock_db)

    assert result is None  # 204 returns None


async def test_delete_party_not_found():
    from app.api.v1.party import delete_party

    mock_db = AsyncMock()

    with patch("app.api.v1.party.PartyRepository") as MockRepo:
        instance = AsyncMock()
        instance.soft_delete.return_value = None
        MockRepo.return_value = instance

        with pytest.raises(NotFoundException):
            await delete_party(party_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db)


# ── get_party_hierarchy ───────────────────────────────────────────────────────


async def test_get_party_hierarchy_delegates_to_service():
    from app.api.v1.party import get_party_hierarchy

    party = _make_party()
    mock_db = AsyncMock()

    with patch("app.api.v1.party.services") as mock_svc_mod:
        mock_svc_mod.get_party_hierarchy = AsyncMock(return_value=[party])

        with patch("app.api.v1.party.Party") as MockModel:
            MockModel.model_validate.return_value = party

            result = await get_party_hierarchy(
                party_id=party.id, tenant_id=TENANT, db=mock_db,
            )

    assert len(result) == 1


# ── party_characteristic ──────────────────────────────────────────────────────


async def test_list_characteristics_empty():
    from app.api.v1.party_characteristic import list_characteristics

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await list_characteristics(
        party_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
    )
    assert result == []


async def test_create_characteristic_party_not_found():
    from app.api.v1.party_characteristic import create_characteristic

    mock_db = AsyncMock()
    mock_party_result = MagicMock()
    mock_party_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_party_result)

    body = PartyCharacteristicCreate(
        party_id=uuid.uuid4(), name="email", value="test@example.com",
    )

    with pytest.raises(NotFoundException):
        await create_characteristic(body=body, tenant_id=TENANT, db=mock_db)


async def test_delete_characteristic_not_found():
    from app.api.v1.party_characteristic import delete_characteristic

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(NotFoundException):
        await delete_characteristic(
            characteristic_id=uuid.uuid4(), tenant_id=TENANT, db=mock_db,
        )


# ── dependencies ──────────────────────────────────────────────────────────────


async def test_get_kafka_producer_returns_producer():
    from app.dependencies import get_kafka_producer

    mock_producer = AsyncMock()
    mock_request = MagicMock()
    mock_request.app.state.kafka_producer = mock_producer

    result = await get_kafka_producer(mock_request)
    assert result is mock_producer


async def test_get_kafka_producer_raises_503_when_missing():
    from fastapi import HTTPException
    from app.dependencies import get_kafka_producer

    mock_request = MagicMock()
    mock_request.app.state.kafka_producer = None

    with pytest.raises(HTTPException) as exc_info:
        await get_kafka_producer(mock_request)
    assert exc_info.value.status_code == 503


def test_get_current_tenant_id_returns_value():
    from app.dependencies import get_current_tenant_id

    mock_request = MagicMock()
    mock_request.state.tenant_id = "tenant-abc"
    result = get_current_tenant_id(mock_request)
    assert result == "tenant-abc"


def test_get_current_tenant_id_raises_400_when_missing():
    from fastapi import HTTPException
    from app.dependencies import get_current_tenant_id

    mock_request = MagicMock()
    mock_request.state.tenant_id = ""

    with pytest.raises(HTTPException) as exc_info:
        get_current_tenant_id(mock_request)
    assert exc_info.value.status_code == 400


def test_get_correlation_id_returns_value():
    from app.dependencies import get_correlation_id

    mock_request = MagicMock()
    mock_request.state.correlation_id = "corr-xyz"
    result = get_correlation_id(mock_request)
    assert result == "corr-xyz"


def test_get_correlation_id_returns_empty_when_missing():
    from app.dependencies import get_correlation_id

    mock_request = MagicMock()
    mock_request.state.correlation_id = ""
    result = get_correlation_id(mock_request)
    assert result == ""


async def test_get_db_commit_path():
    from app.dependencies import get_db

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
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

    with patch("app.dependencies.AsyncSessionLocal", return_value=mock_ctx):
        gen = get_db()
        await gen.__anext__()
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("db error"))

    mock_session.rollback.assert_awaited_once()
