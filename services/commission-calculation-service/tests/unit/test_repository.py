"""Unit tests for commission-calculation-service repository layer.

Uses SQLite in-memory via aiosqlite so no Postgres is required.
UUID columns use postgresql.UUID(as_uuid=True); SQLite stores them as strings
but the ORM accepts uuid.UUID objects transparently when as_uuid=True.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.models import CommissionEventStatus, CommissionStatementStatus
from app.infrastructure.db.repository import (
    CommissionEventRepository,
    CommissionStatementRepository,
    ProcessedEventLogRepository,
)

pytestmark = pytest.mark.asyncio

TENANT = "tenant-test-001"
OTHER_TENANT = "tenant-other-999"


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(UTC)


async def _create_event(
    repo: CommissionEventRepository,
    *,
    party_id: uuid.UUID | None = None,
    commission_amount: float = 10.0,
    base_amount: float = 100.0,
    quantity: int = 1,
    currency: str = "USD",
    status_override: CommissionEventStatus | None = None,
    calculation_date: datetime | None = None,
    tenant_id: str = TENANT,
) -> object:
    event = await repo.create(
        source_transaction_id=uuid.uuid4(),
        party_id=party_id or uuid.uuid4(),
        agreement_id=uuid.uuid4(),
        rule_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity=quantity,
        base_amount=base_amount,
        commission_amount=commission_amount,
        currency=currency,
        calculation_date=calculation_date or _now(),
        tenant_id=tenant_id,
    )
    if status_override is not None:
        event = await repo.update_status(event.id, status_override, tenant_id)
    return event


# ─── CommissionEventRepository ────────────────────────────────────────────────


class TestCommissionEventRepositoryCreate:
    async def test_create_returns_domain_model(self, db_session):
        repo = CommissionEventRepository(db_session)
        party_id = uuid.uuid4()
        event = await _create_event(repo, party_id=party_id)

        assert event.id is not None
        assert isinstance(event.id, uuid.UUID)
        assert event.party_id == party_id
        assert event.commission_amount == 10.0
        assert event.status == CommissionEventStatus.CALCULATED
        assert event.tenant_id == TENANT

    async def test_create_sets_created_at(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)
        assert event.created_at is not None

    async def test_create_multiple_events(self, db_session):
        repo = CommissionEventRepository(db_session)
        e1 = await _create_event(repo)
        e2 = await _create_event(repo)
        assert e1.id != e2.id


class TestCommissionEventRepositoryGetById:
    async def test_get_by_id_found(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)

        fetched = await repo.get_by_id(event.id, TENANT)
        assert fetched is not None
        assert fetched.id == event.id
        assert fetched.tenant_id == TENANT

    async def test_get_by_id_not_found_returns_none(self, db_session):
        repo = CommissionEventRepository(db_session)

        result = await repo.get_by_id(uuid.uuid4(), TENANT)
        assert result is None

    async def test_get_by_id_wrong_tenant_returns_none(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)

        result = await repo.get_by_id(event.id, OTHER_TENANT)
        assert result is None


class TestCommissionEventRepositoryListWithFilters:
    async def test_list_empty_returns_empty_and_zero(self, db_session):
        repo = CommissionEventRepository(db_session)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert items == []
        assert total == 0

    async def test_list_no_filters_returns_all(self, db_session):
        repo = CommissionEventRepository(db_session)
        await _create_event(repo)
        await _create_event(repo)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert total == 2
        assert len(items) == 2

    async def test_list_tenant_isolation(self, db_session):
        repo = CommissionEventRepository(db_session)
        await _create_event(repo, tenant_id=TENANT)
        await _create_event(repo, tenant_id=OTHER_TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert total == 1
        assert all(e.tenant_id == TENANT for e in items)

    async def test_list_filter_by_party_id(self, db_session):
        repo = CommissionEventRepository(db_session)
        target_party = uuid.uuid4()
        await _create_event(repo, party_id=target_party)
        await _create_event(repo)  # different party

        items, total = await repo.list_with_filters(tenant_id=TENANT, party_id=target_party)
        assert total == 1
        assert items[0].party_id == target_party

    async def test_list_filter_by_status(self, db_session):
        repo = CommissionEventRepository(db_session)
        await _create_event(repo, status_override=CommissionEventStatus.APPROVED)
        await _create_event(repo)  # stays CALCULATED

        items, total = await repo.list_with_filters(
            tenant_id=TENANT, status=CommissionEventStatus.APPROVED
        )
        assert total == 1
        assert items[0].status == CommissionEventStatus.APPROVED

    async def test_list_filter_by_from_date(self, db_session):
        repo = CommissionEventRepository(db_session)
        past = datetime(2024, 1, 1, tzinfo=UTC)
        future = datetime(2030, 1, 1, tzinfo=UTC)
        await _create_event(repo, calculation_date=past)
        await _create_event(repo, calculation_date=future)

        # only the future event should be returned
        cutoff = datetime(2025, 1, 1, tzinfo=UTC)
        items, total = await repo.list_with_filters(tenant_id=TENANT, from_date=cutoff)
        assert total == 1

    async def test_list_filter_by_to_date(self, db_session):
        repo = CommissionEventRepository(db_session)
        past = datetime(2024, 1, 1, tzinfo=UTC)
        future = datetime(2030, 1, 1, tzinfo=UTC)
        await _create_event(repo, calculation_date=past)
        await _create_event(repo, calculation_date=future)

        # only the past event should be returned
        cutoff = datetime(2025, 1, 1, tzinfo=UTC)
        items, total = await repo.list_with_filters(tenant_id=TENANT, to_date=cutoff)
        assert total == 1

    async def test_list_pagination_page_size(self, db_session):
        repo = CommissionEventRepository(db_session)
        for _ in range(5):
            await _create_event(repo)

        items, total = await repo.list_with_filters(tenant_id=TENANT, page=1, size=2)
        assert total == 5
        assert len(items) == 2

    async def test_list_pagination_second_page(self, db_session):
        repo = CommissionEventRepository(db_session)
        for _ in range(5):
            await _create_event(repo)

        items_p1, _ = await repo.list_with_filters(tenant_id=TENANT, page=1, size=3)
        items_p2, _ = await repo.list_with_filters(tenant_id=TENANT, page=2, size=3)
        ids_p1 = {e.id for e in items_p1}
        ids_p2 = {e.id for e in items_p2}
        assert len(ids_p2) == 2
        assert ids_p1.isdisjoint(ids_p2)

    async def test_list_all_filters_combined(self, db_session):
        repo = CommissionEventRepository(db_session)
        party = uuid.uuid4()
        calc_date = datetime(2026, 6, 1, tzinfo=UTC)
        await _create_event(repo, party_id=party, calculation_date=calc_date)
        await _create_event(repo)  # different party/date

        items, total = await repo.list_with_filters(
            tenant_id=TENANT,
            party_id=party,
            from_date=datetime(2026, 1, 1, tzinfo=UTC),
            to_date=datetime(2026, 12, 31, tzinfo=UTC),
            status=CommissionEventStatus.CALCULATED,
        )
        assert total == 1
        assert items[0].party_id == party


class TestCommissionEventRepositoryUpdateStatus:
    async def test_update_status_changes_status(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)
        assert event.status == CommissionEventStatus.CALCULATED

        updated = await repo.update_status(
            event.id, CommissionEventStatus.APPROVED, TENANT
        )
        assert updated is not None
        assert updated.status == CommissionEventStatus.APPROVED
        assert updated.id == event.id

    async def test_update_status_not_found_returns_none(self, db_session):
        repo = CommissionEventRepository(db_session)

        result = await repo.update_status(uuid.uuid4(), CommissionEventStatus.APPROVED, TENANT)
        assert result is None

    async def test_update_status_wrong_tenant_returns_none(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)

        result = await repo.update_status(event.id, CommissionEventStatus.APPROVED, OTHER_TENANT)
        assert result is None

    async def test_update_status_to_disputed(self, db_session):
        repo = CommissionEventRepository(db_session)
        event = await _create_event(repo)

        updated = await repo.update_status(
            event.id, CommissionEventStatus.DISPUTED, TENANT
        )
        assert updated.status == CommissionEventStatus.DISPUTED


# ─── CommissionStatementRepository ────────────────────────────────────────────


class TestCommissionStatementRepositoryGetOrCreateDraft:
    async def test_creates_draft_when_none_exists(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        stmt = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=1, currency="USD", tenant_id=TENANT
        )

        assert stmt.id is not None
        assert stmt.party_id == party_id
        assert stmt.period_year == 2026
        assert stmt.period_month == 1
        assert stmt.status == CommissionStatementStatus.DRAFT
        assert stmt.total_commission == 0.0
        assert stmt.line_items_count == 0
        assert stmt.tenant_id == TENANT

    async def test_returns_existing_draft_unchanged(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        first = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=2, currency="USD", tenant_id=TENANT
        )
        second = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=2, currency="USD", tenant_id=TENANT
        )

        assert first.id == second.id
        assert second.total_commission == 0.0

    async def test_different_months_create_separate_drafts(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        jan = await repo.get_or_create_draft(party_id=party_id, year=2026, month=1, currency="USD", tenant_id=TENANT)
        feb = await repo.get_or_create_draft(party_id=party_id, year=2026, month=2, currency="USD", tenant_id=TENANT)

        assert jan.id != feb.id
        assert jan.period_month == 1
        assert feb.period_month == 2


class TestCommissionStatementRepositoryAddCommission:
    async def test_creates_statement_with_first_commission(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        stmt = await repo.add_commission_to_draft(
            party_id=party_id,
            year=2026,
            month=3,
            currency="USD",
            tenant_id=TENANT,
            commission_amount=25.50,
        )

        assert stmt.total_commission == 25.50
        assert stmt.line_items_count == 1
        assert stmt.status == CommissionStatementStatus.DRAFT

    async def test_accumulates_commission_on_existing_statement(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        await repo.add_commission_to_draft(
            party_id=party_id, year=2026, month=4, currency="USD",
            tenant_id=TENANT, commission_amount=10.0,
        )
        stmt = await repo.add_commission_to_draft(
            party_id=party_id, year=2026, month=4, currency="USD",
            tenant_id=TENANT, commission_amount=5.0,
        )

        assert stmt.total_commission == 15.0
        assert stmt.line_items_count == 2

    async def test_accumulates_multiple_commissions(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        amounts = [10.0, 20.0, 7.5, 2.5]
        for amount in amounts:
            stmt = await repo.add_commission_to_draft(
                party_id=party_id, year=2026, month=5, currency="USD",
                tenant_id=TENANT, commission_amount=amount,
            )

        assert stmt.total_commission == 40.0
        assert stmt.line_items_count == 4


class TestCommissionStatementRepositoryConfirm:
    async def test_confirm_sets_confirmed_status(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        draft = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=6, currency="USD", tenant_id=TENANT
        )

        confirmed = await repo.confirm(draft.id, TENANT)
        assert confirmed is not None
        assert confirmed.status == CommissionStatementStatus.CONFIRMED
        assert confirmed.confirmed_at is not None
        assert confirmed.id == draft.id

    async def test_confirm_not_found_returns_none(self, db_session):
        repo = CommissionStatementRepository(db_session)

        result = await repo.confirm(uuid.uuid4(), TENANT)
        assert result is None

    async def test_confirm_wrong_tenant_returns_none(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        draft = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=7, currency="USD", tenant_id=TENANT
        )

        result = await repo.confirm(draft.id, OTHER_TENANT)
        assert result is None


class TestCommissionStatementRepositoryGetById:
    async def test_get_by_id_found(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        draft = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=8, currency="USD", tenant_id=TENANT
        )

        fetched = await repo.get_by_id(draft.id, TENANT)
        assert fetched is not None
        assert fetched.id == draft.id
        assert fetched.party_id == party_id

    async def test_get_by_id_not_found_returns_none(self, db_session):
        repo = CommissionStatementRepository(db_session)

        result = await repo.get_by_id(uuid.uuid4(), TENANT)
        assert result is None

    async def test_get_by_id_wrong_tenant_returns_none(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()

        draft = await repo.get_or_create_draft(
            party_id=party_id, year=2026, month=9, currency="USD", tenant_id=TENANT
        )

        result = await repo.get_by_id(draft.id, OTHER_TENANT)
        assert result is None


class TestCommissionStatementRepositoryListWithFilters:
    async def test_list_empty_returns_empty_and_zero(self, db_session):
        repo = CommissionStatementRepository(db_session)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert items == []
        assert total == 0

    async def test_list_no_filters_returns_all(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=1, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=2, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert total == 2
        assert len(items) == 2

    async def test_list_tenant_isolation(self, db_session):
        repo = CommissionStatementRepository(db_session)
        await repo.get_or_create_draft(party_id=uuid.uuid4(), year=2026, month=1, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=uuid.uuid4(), year=2026, month=1, currency="USD", tenant_id=OTHER_TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT)
        assert total == 1
        assert all(s.tenant_id == TENANT for s in items)

    async def test_list_filter_by_party_id(self, db_session):
        repo = CommissionStatementRepository(db_session)
        target_party = uuid.uuid4()
        await repo.get_or_create_draft(party_id=target_party, year=2026, month=1, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=uuid.uuid4(), year=2026, month=1, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT, party_id=target_party)
        assert total == 1
        assert items[0].party_id == target_party

    async def test_list_filter_by_year(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()
        await repo.get_or_create_draft(party_id=party_id, year=2025, month=1, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=1, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT, year=2026)
        assert total == 1
        assert items[0].period_year == 2026

    async def test_list_filter_by_month(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=3, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=4, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT, month=3)
        assert total == 1
        assert items[0].period_month == 3

    async def test_list_pagination(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()
        for month in range(1, 6):
            await repo.get_or_create_draft(party_id=party_id, year=2026, month=month, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(tenant_id=TENANT, page=1, size=2)
        assert total == 5
        assert len(items) == 2

    async def test_list_all_filters_combined(self, db_session):
        repo = CommissionStatementRepository(db_session)
        party_id = uuid.uuid4()
        await repo.get_or_create_draft(party_id=party_id, year=2026, month=6, currency="USD", tenant_id=TENANT)
        await repo.get_or_create_draft(party_id=uuid.uuid4(), year=2026, month=6, currency="USD", tenant_id=TENANT)

        items, total = await repo.list_with_filters(
            tenant_id=TENANT, party_id=party_id, year=2026, month=6
        )
        assert total == 1
        assert items[0].party_id == party_id


# ─── ProcessedEventLogRepository ──────────────────────────────────────────────


class TestProcessedEventLogRepository:
    async def test_is_processed_false_before_marking(self, db_session):
        repo = ProcessedEventLogRepository(db_session)
        txn_id = uuid.uuid4()
        agreement_id = str(uuid.uuid4())

        result = await repo.is_processed(txn_id, agreement_id)
        assert result is False

    async def test_mark_and_is_processed_true(self, db_session):
        repo = ProcessedEventLogRepository(db_session)
        txn_id = uuid.uuid4()
        agreement_id = str(uuid.uuid4())

        await repo.mark_processed(txn_id, agreement_id)
        await db_session.commit()

        result = await repo.is_processed(txn_id, agreement_id)
        assert result is True

    async def test_different_pair_not_processed(self, db_session):
        repo = ProcessedEventLogRepository(db_session)
        txn_id = uuid.uuid4()
        agreement_id = str(uuid.uuid4())

        await repo.mark_processed(txn_id, agreement_id)
        await db_session.commit()

        # Different transaction id
        result = await repo.is_processed(uuid.uuid4(), agreement_id)
        assert result is False

    async def test_mark_processed_duplicate_ignored(self, db_session):
        """Duplicate mark_processed should not raise (IntegrityError is swallowed)."""
        repo = ProcessedEventLogRepository(db_session)
        txn_id = uuid.uuid4()
        agreement_id = str(uuid.uuid4())

        await repo.mark_processed(txn_id, agreement_id)
        await db_session.commit()
        # Second call with the same pair — must not raise
        await repo.mark_processed(txn_id, agreement_id)
