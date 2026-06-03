"""Repository pattern for commission-calculation-service persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    CommissionEvent,
    CommissionEventStatus,
    CommissionStatement,
    CommissionStatementStatus,
)
from app.infrastructure.db import models as db_models

log = structlog.get_logger(__name__)


# ─── Mapping helpers ──────────────────────────────────────────────────────────

def _event_to_domain(db_ev: db_models.CommissionEvent) -> CommissionEvent:
    return CommissionEvent(
        id=db_ev.id,
        source_transaction_id=db_ev.source_transaction_id,
        party_id=db_ev.party_id,
        agreement_id=db_ev.agreement_id,
        rule_id=db_ev.rule_id,
        product_id=db_ev.product_id,
        quantity=db_ev.quantity,
        base_amount=db_ev.base_amount,
        commission_amount=db_ev.commission_amount,
        currency=db_ev.currency,
        calculation_date=db_ev.calculation_date,
        status=CommissionEventStatus(db_ev.status),
        tenant_id=db_ev.tenant_id,
        created_at=db_ev.created_at,
    )


def _statement_to_domain(db_stmt: db_models.CommissionStatement) -> CommissionStatement:
    return CommissionStatement(
        id=db_stmt.id,
        party_id=db_stmt.party_id,
        period_year=db_stmt.period_year,
        period_month=db_stmt.period_month,
        total_commission=db_stmt.total_commission,
        currency=db_stmt.currency,
        line_items_count=db_stmt.line_items_count,
        status=CommissionStatementStatus(db_stmt.status),
        confirmed_at=db_stmt.confirmed_at,
        tenant_id=db_stmt.tenant_id,
    )


# ─── CommissionEventRepository ────────────────────────────────────────────────

class CommissionEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        source_transaction_id: uuid.UUID,
        party_id: uuid.UUID,
        agreement_id: uuid.UUID,
        rule_id: uuid.UUID,
        product_id: uuid.UUID,
        quantity: int,
        base_amount: float,
        commission_amount: float,
        currency: str,
        calculation_date: datetime,
        tenant_id: str,
    ) -> CommissionEvent:
        db_ev = db_models.CommissionEvent(
            source_transaction_id=source_transaction_id,
            party_id=party_id,
            agreement_id=agreement_id,
            rule_id=rule_id,
            product_id=product_id,
            quantity=quantity,
            base_amount=base_amount,
            commission_amount=commission_amount,
            currency=currency,
            calculation_date=calculation_date,
            status=CommissionEventStatus.CALCULATED.value,
            tenant_id=tenant_id,
        )
        self._session.add(db_ev)
        await self._session.flush()
        await self._session.refresh(db_ev)

        log.info(
            "commission_event.created",
            event_id=str(db_ev.id),
            source_transaction_id=str(source_transaction_id),
            party_id=str(party_id),
            commission_amount=commission_amount,
            tenant_id=tenant_id,
        )
        return _event_to_domain(db_ev)

    async def get_by_id(
        self, event_id: uuid.UUID, tenant_id: str
    ) -> CommissionEvent | None:
        result = await self._session.execute(
            select(db_models.CommissionEvent).where(
                db_models.CommissionEvent.id == event_id,
                db_models.CommissionEvent.tenant_id == tenant_id,
            )
        )
        db_ev = result.scalar_one_or_none()
        return _event_to_domain(db_ev) if db_ev else None

    async def list_with_filters(
        self,
        tenant_id: str,
        party_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        status: CommissionEventStatus | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CommissionEvent], int]:
        query = select(db_models.CommissionEvent).where(
            db_models.CommissionEvent.tenant_id == tenant_id
        )
        count_q = select(func.count(db_models.CommissionEvent.id)).where(
            db_models.CommissionEvent.tenant_id == tenant_id
        )

        if party_id is not None:
            query = query.where(db_models.CommissionEvent.party_id == party_id)
            count_q = count_q.where(db_models.CommissionEvent.party_id == party_id)
        if from_date is not None:
            query = query.where(db_models.CommissionEvent.calculation_date >= from_date)
            count_q = count_q.where(db_models.CommissionEvent.calculation_date >= from_date)
        if to_date is not None:
            query = query.where(db_models.CommissionEvent.calculation_date <= to_date)
            count_q = count_q.where(db_models.CommissionEvent.calculation_date <= to_date)
        if status is not None:
            query = query.where(db_models.CommissionEvent.status == status.value)
            count_q = count_q.where(db_models.CommissionEvent.status == status.value)

        offset = (page - 1) * size
        query = (
            query.order_by(db_models.CommissionEvent.calculation_date.desc())
            .offset(offset)
            .limit(size)
        )

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(query)
        items = result.scalars().all()
        return [_event_to_domain(ev) for ev in items], total

    async def update_status(
        self,
        event_id: uuid.UUID,
        new_status: CommissionEventStatus,
        tenant_id: str,
    ) -> CommissionEvent | None:
        db_ev = await self._session.get(db_models.CommissionEvent, event_id)
        if db_ev is None or db_ev.tenant_id != tenant_id:
            return None
        db_ev.status = new_status.value
        await self._session.flush()
        await self._session.refresh(db_ev)
        return _event_to_domain(db_ev)


# ─── CommissionStatementRepository ────────────────────────────────────────────

class CommissionStatementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_draft(
        self,
        party_id: uuid.UUID,
        year: int,
        month: int,
        currency: str,
        tenant_id: str,
    ) -> CommissionStatement:
        """
        Upsert a DRAFT statement for the given party/period.
        If it already exists and is DRAFT, return it unchanged.
        """
        result = await self._session.execute(
            select(db_models.CommissionStatement).where(
                db_models.CommissionStatement.party_id == party_id,
                db_models.CommissionStatement.period_year == year,
                db_models.CommissionStatement.period_month == month,
                db_models.CommissionStatement.tenant_id == tenant_id,
            )
        )
        db_stmt = result.scalar_one_or_none()

        if db_stmt is None:
            db_stmt = db_models.CommissionStatement(
                party_id=party_id,
                period_year=year,
                period_month=month,
                total_commission=0.0,
                currency=currency,
                line_items_count=0,
                status=CommissionStatementStatus.DRAFT.value,
                tenant_id=tenant_id,
            )
            self._session.add(db_stmt)
            await self._session.flush()
            await self._session.refresh(db_stmt)
            log.info(
                "commission_statement.draft_created",
                statement_id=str(db_stmt.id),
                party_id=str(party_id),
                period=f"{year}-{month:02d}",
                tenant_id=tenant_id,
            )

        return _statement_to_domain(db_stmt)

    async def add_commission_to_draft(
        self,
        party_id: uuid.UUID,
        year: int,
        month: int,
        currency: str,
        tenant_id: str,
        commission_amount: float,
    ) -> CommissionStatement:
        """
        Add commission_amount to the running total of the DRAFT statement,
        creating the statement if it doesn't yet exist.
        """
        result = await self._session.execute(
            select(db_models.CommissionStatement).where(
                db_models.CommissionStatement.party_id == party_id,
                db_models.CommissionStatement.period_year == year,
                db_models.CommissionStatement.period_month == month,
                db_models.CommissionStatement.tenant_id == tenant_id,
            )
        )
        db_stmt = result.scalar_one_or_none()

        if db_stmt is None:
            db_stmt = db_models.CommissionStatement(
                party_id=party_id,
                period_year=year,
                period_month=month,
                total_commission=commission_amount,
                currency=currency,
                line_items_count=1,
                status=CommissionStatementStatus.DRAFT.value,
                tenant_id=tenant_id,
            )
            self._session.add(db_stmt)
        else:
            db_stmt.total_commission = round(
                db_stmt.total_commission + commission_amount, 2
            )
            db_stmt.line_items_count += 1

        await self._session.flush()
        await self._session.refresh(db_stmt)
        return _statement_to_domain(db_stmt)

    async def confirm(
        self, statement_id: uuid.UUID, tenant_id: str
    ) -> CommissionStatement | None:
        db_stmt = await self._session.get(db_models.CommissionStatement, statement_id)
        if db_stmt is None or db_stmt.tenant_id != tenant_id:
            return None
        db_stmt.status = CommissionStatementStatus.CONFIRMED.value
        db_stmt.confirmed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(db_stmt)
        log.info(
            "commission_statement.confirmed",
            statement_id=str(statement_id),
            tenant_id=tenant_id,
        )
        return _statement_to_domain(db_stmt)

    async def get_by_id(
        self, statement_id: uuid.UUID, tenant_id: str
    ) -> CommissionStatement | None:
        result = await self._session.execute(
            select(db_models.CommissionStatement).where(
                db_models.CommissionStatement.id == statement_id,
                db_models.CommissionStatement.tenant_id == tenant_id,
            )
        )
        db_stmt = result.scalar_one_or_none()
        return _statement_to_domain(db_stmt) if db_stmt else None

    async def list_with_filters(
        self,
        tenant_id: str,
        party_id: uuid.UUID | None = None,
        year: int | None = None,
        month: int | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CommissionStatement], int]:
        query = select(db_models.CommissionStatement).where(
            db_models.CommissionStatement.tenant_id == tenant_id
        )
        count_q = select(func.count(db_models.CommissionStatement.id)).where(
            db_models.CommissionStatement.tenant_id == tenant_id
        )

        if party_id is not None:
            query = query.where(db_models.CommissionStatement.party_id == party_id)
            count_q = count_q.where(db_models.CommissionStatement.party_id == party_id)
        if year is not None:
            query = query.where(db_models.CommissionStatement.period_year == year)
            count_q = count_q.where(db_models.CommissionStatement.period_year == year)
        if month is not None:
            query = query.where(db_models.CommissionStatement.period_month == month)
            count_q = count_q.where(db_models.CommissionStatement.period_month == month)

        offset = (page - 1) * size
        query = (
            query.order_by(
                db_models.CommissionStatement.period_year.desc(),
                db_models.CommissionStatement.period_month.desc(),
            )
            .offset(offset)
            .limit(size)
        )

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(query)
        stmts = result.scalars().all()
        return [_statement_to_domain(s) for s in stmts], total


# ─── ProcessedEventLogRepository ─────────────────────────────────────────────

class ProcessedEventLogRepository:
    """Idempotency guard — prevents double-processing of the same event."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_processed(
        self,
        source_transaction_id: uuid.UUID,
        agreement_id: str,
    ) -> bool:
        """Return True if this (transaction_id, agreement_id) pair was already processed."""
        result = await self._session.execute(
            select(db_models.ProcessedEventLog.id).where(
                db_models.ProcessedEventLog.source_transaction_id == source_transaction_id,
                db_models.ProcessedEventLog.agreement_id == agreement_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def mark_processed(
        self,
        source_transaction_id: uuid.UUID,
        agreement_id: str,
    ) -> None:
        """Record that this (transaction_id, agreement_id) has been processed."""
        log_entry = db_models.ProcessedEventLog(
            source_transaction_id=source_transaction_id,
            agreement_id=agreement_id,
        )
        # Use a SAVEPOINT so a concurrent-duplicate collision rolls back only
        # this insert — never the surrounding transaction (which holds the
        # legitimately-created commission event).
        try:
            async with self._session.begin_nested():
                self._session.add(log_entry)
                await self._session.flush()
        except IntegrityError:
            # Concurrent duplicate — already processed, safe to ignore.
            log.warning(
                "processed_event_log.duplicate_ignored",
                source_transaction_id=str(source_transaction_id),
                agreement_id=agreement_id,
            )
