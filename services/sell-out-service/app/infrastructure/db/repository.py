"""Repository pattern for SaleTransaction persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    PosSession,
    PosSessionCreate,
    PosSessionStatus,
    ReturnCondition,
    ReturnStatus,
    ReturnTransaction,
    ReturnTransactionCreate,
    ReturnTransactionItem,
    SaleStatus,
    SaleTransaction,
    SaleTransactionCreate,
    SaleTransactionItem,
    SaleTransactionItemCreate,
    SaleTransactionSummary,
)
from app.infrastructure.db import models as db_models

logger = structlog.get_logger(__name__)


def _item_to_domain(db_item: db_models.SaleTransactionItem) -> SaleTransactionItem:
    return SaleTransactionItem(
        id=db_item.id,
        product_id=db_item.product_id,
        product_name=db_item.product_name,
        quantity=db_item.quantity,
        unit_price=db_item.unit_price,
        discount_amount=db_item.discount_amount,
        serial_numbers=db_item.serial_numbers or [],
        commission_eligible=db_item.commission_eligible,
    )


def _txn_to_domain(db_txn: db_models.SaleTransaction) -> SaleTransaction:
    return SaleTransaction(
        id=db_txn.id,
        transaction_number=db_txn.transaction_number,
        dealer_party_id=db_txn.dealer_party_id,
        customer_party_id=db_txn.customer_party_id,
        channel=db_txn.channel,  # type: ignore[arg-type]
        items=[_item_to_domain(i) for i in db_txn.items],
        total_amount=db_txn.total_amount,
        currency=db_txn.currency,
        status=db_txn.status,  # type: ignore[arg-type]
        pos_session_id=db_txn.pos_session_id,
        payment_method=db_txn.payment_method,
        payment_reference=db_txn.payment_reference,
        tenant_id=db_txn.tenant_id,
        created_at=db_txn.created_at,
        updated_at=db_txn.updated_at,
    )


class SaleTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        transaction_data: SaleTransactionCreate,
        items_data: list[SaleTransactionItemCreate],
        tenant_id: str,
        transaction_number: str,
        total_amount: float,
    ) -> SaleTransaction:
        """Create a sale transaction with its items in a single DB transaction."""
        db_txn = db_models.SaleTransaction(
            transaction_number=transaction_number,
            dealer_party_id=transaction_data.dealer_party_id,
            customer_party_id=transaction_data.customer_party_id,
            channel=transaction_data.channel.value,
            total_amount=total_amount,
            currency="USD",
            status=SaleStatus.COMPLETED.value,
            pos_session_id=transaction_data.pos_session_id,
            payment_method=transaction_data.payment_method.value if transaction_data.payment_method else None,
            payment_reference=transaction_data.payment_reference,
            tenant_id=tenant_id,
        )
        self._session.add(db_txn)
        await self._session.flush()  # get db_txn.id before items

        for item in items_data:
            db_item = db_models.SaleTransactionItem(
                transaction_id=db_txn.id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
                serial_numbers=item.serial_numbers,
                commission_eligible=item.commission_eligible,
            )
            self._session.add(db_item)

        await self._session.flush()
        await self._session.refresh(db_txn)

        log = logger.bind(
            transaction_id=str(db_txn.id),
            transaction_number=transaction_number,
            tenant_id=tenant_id,
        )
        log.info("sale_transaction.created")
        return _txn_to_domain(db_txn)

    async def get_by_id(
        self, transaction_id: uuid.UUID, tenant_id: str
    ) -> SaleTransaction | None:
        result = await self._session.execute(
            select(db_models.SaleTransaction).where(
                db_models.SaleTransaction.id == transaction_id,
                db_models.SaleTransaction.tenant_id == tenant_id,
            )
        )
        db_txn = result.scalar_one_or_none()
        return _txn_to_domain(db_txn) if db_txn else None

    async def list_with_filters(
        self,
        tenant_id: str,
        dealer_party_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        status: SaleStatus | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[SaleTransaction], int]:
        """Return paginated transactions and total count."""
        query = select(db_models.SaleTransaction).where(
            db_models.SaleTransaction.tenant_id == tenant_id
        )
        count_query = select(func.count(db_models.SaleTransaction.id)).where(
            db_models.SaleTransaction.tenant_id == tenant_id
        )

        if dealer_party_id is not None:
            query = query.where(
                db_models.SaleTransaction.dealer_party_id == dealer_party_id
            )
            count_query = count_query.where(
                db_models.SaleTransaction.dealer_party_id == dealer_party_id
            )
        if from_date is not None:
            query = query.where(db_models.SaleTransaction.created_at >= from_date)
            count_query = count_query.where(
                db_models.SaleTransaction.created_at >= from_date
            )
        if to_date is not None:
            query = query.where(db_models.SaleTransaction.created_at <= to_date)
            count_query = count_query.where(
                db_models.SaleTransaction.created_at <= to_date
            )
        if status is not None:
            query = query.where(db_models.SaleTransaction.status == status.value)
            count_query = count_query.where(
                db_models.SaleTransaction.status == status.value
            )

        offset = (page - 1) * size
        query = query.order_by(db_models.SaleTransaction.created_at.desc()).offset(offset).limit(size)

        total_result = await self._session.execute(count_query)
        total_count = total_result.scalar_one()

        result = await self._session.execute(query)
        db_txns = result.scalars().all()

        return [_txn_to_domain(t) for t in db_txns], total_count

    async def update_status(
        self,
        transaction_id: uuid.UUID,
        status: SaleStatus,
        tenant_id: str,
    ) -> SaleTransaction | None:
        db_txn = await self._session.get(db_models.SaleTransaction, transaction_id)
        if db_txn is None or db_txn.tenant_id != tenant_id:
            return None
        db_txn.status = status.value
        await self._session.flush()
        await self._session.refresh(db_txn)
        logger.info(
            "sale_transaction.status_updated",
            transaction_id=str(transaction_id),
            new_status=status.value,
            tenant_id=tenant_id,
        )
        return _txn_to_domain(db_txn)

    async def get_summary(
        self,
        dealer_party_id: uuid.UUID,
        period: str,
        tenant_id: str,
    ) -> SaleTransactionSummary:
        """Aggregate summary for a dealer over a period (YYYY-MM format)."""
        # Parse period
        try:
            year_str, month_str = period.split("-")
            year, month = int(year_str), int(month_str)
        except (ValueError, AttributeError):
            year, month = None, None

        query = select(db_models.SaleTransaction).where(
            db_models.SaleTransaction.dealer_party_id == dealer_party_id,
            db_models.SaleTransaction.tenant_id == tenant_id,
            db_models.SaleTransaction.status != SaleStatus.REVERSED.value,
        )
        if year is not None and month is not None:
            from sqlalchemy import extract

            query = query.where(
                extract("year", db_models.SaleTransaction.created_at) == year,
                extract("month", db_models.SaleTransaction.created_at) == month,
            )

        result = await self._session.execute(query)
        transactions = result.scalars().all()

        total_transactions = len(transactions)
        total_amount = sum(t.total_amount for t in transactions)

        # Fetch items for all transactions to sum units
        item_query = select(db_models.SaleTransactionItem).where(
            db_models.SaleTransactionItem.transaction_id.in_(
                [t.id for t in transactions]
            )
        )
        item_result = await self._session.execute(item_query)
        items = item_result.scalars().all()
        total_units = sum(i.quantity for i in items)

        return SaleTransactionSummary(
            dealer_party_id=dealer_party_id,
            period=period,
            total_transactions=total_transactions,
            total_units=total_units,
            total_amount=round(total_amount, 2),
            currency="USD",
        )


def _session_to_domain(db_s: db_models.PosSession) -> PosSession:
    return PosSession(
        id=db_s.id,
        terminal_id=db_s.terminal_id,
        dealer_party_id=db_s.dealer_party_id,
        opened_by=db_s.opened_by,
        opened_at=db_s.opened_at,
        closed_at=db_s.closed_at,
        status=db_s.status,  # type: ignore[arg-type]
        opening_cash=db_s.opening_cash,
        closing_cash=db_s.closing_cash,
        total_transactions=db_s.total_transactions,
        total_amount=db_s.total_amount,
        tenant_id=db_s.tenant_id,
        created_at=db_s.created_at,
        updated_at=db_s.updated_at,
    )


class PosSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: PosSessionCreate, tenant_id: str) -> PosSession:
        db_s = db_models.PosSession(
            terminal_id=data.terminal_id,
            dealer_party_id=data.dealer_party_id,
            opened_by=data.opened_by,
            opened_at=datetime.now(UTC).isoformat(),
            status=PosSessionStatus.OPEN.value,
            opening_cash=data.opening_cash,
            tenant_id=tenant_id,
        )
        self._session.add(db_s)
        await self._session.flush()
        await self._session.refresh(db_s)
        return _session_to_domain(db_s)

    async def get_by_id(self, session_id: uuid.UUID, tenant_id: str) -> PosSession | None:
        result = await self._session.execute(
            select(db_models.PosSession).where(
                db_models.PosSession.id == session_id,
                db_models.PosSession.tenant_id == tenant_id,
            )
        )
        db_s = result.scalar_one_or_none()
        return _session_to_domain(db_s) if db_s else None

    async def close(self, session_id: uuid.UUID, tenant_id: str, closing_cash: float) -> PosSession | None:
        db_s = await self._session.get(db_models.PosSession, session_id)
        if db_s is None or db_s.tenant_id != tenant_id:
            return None
        db_s.status = PosSessionStatus.CLOSED.value
        db_s.closed_at = datetime.now(UTC).isoformat()
        db_s.closing_cash = closing_cash
        await self._session.flush()
        await self._session.refresh(db_s)
        return _session_to_domain(db_s)


def _return_item_to_domain(db_item: db_models.ReturnTransactionItem) -> ReturnTransactionItem:
    return ReturnTransactionItem(
        id=db_item.id,
        return_transaction_id=db_item.return_transaction_id,
        product_id=db_item.product_id,
        quantity=db_item.quantity,
        serial_numbers=db_item.serial_numbers or [],
        condition=db_item.condition,  # type: ignore[arg-type]
        tenant_id=db_item.tenant_id,
    )


def _return_to_domain(db_r: db_models.ReturnTransaction) -> ReturnTransaction:
    return ReturnTransaction(
        id=db_r.id,
        return_number=db_r.return_number,
        original_transaction_id=db_r.original_transaction_id,
        return_reason=db_r.return_reason,
        status=db_r.status,  # type: ignore[arg-type]
        returned_by=db_r.returned_by,
        returned_at=db_r.returned_at,
        items=[_return_item_to_domain(i) for i in (db_r.items or [])],
        tenant_id=db_r.tenant_id,
        created_at=db_r.created_at,
        updated_at=db_r.updated_at,
    )


class ReturnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ReturnTransactionCreate, tenant_id: str) -> ReturnTransaction:
        return_number = f"RET-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        db_r = db_models.ReturnTransaction(
            return_number=return_number,
            original_transaction_id=data.original_transaction_id,
            return_reason=data.return_reason,
            status=ReturnStatus.PENDING.value,
            returned_by=data.returned_by,
            returned_at=datetime.now(UTC).isoformat(),
            tenant_id=tenant_id,
        )
        self._session.add(db_r)
        await self._session.flush()
        for item in data.items:
            db_item = db_models.ReturnTransactionItem(
                return_transaction_id=db_r.id,
                product_id=item.product_id,
                quantity=item.quantity,
                serial_numbers=item.serial_numbers,
                condition=item.condition.value,
                tenant_id=tenant_id,
            )
            self._session.add(db_item)
        await self._session.flush()
        await self._session.refresh(db_r)
        return _return_to_domain(db_r)

    async def get_by_id(self, return_id: uuid.UUID, tenant_id: str) -> ReturnTransaction | None:
        result = await self._session.execute(
            select(db_models.ReturnTransaction).where(
                db_models.ReturnTransaction.id == return_id,
                db_models.ReturnTransaction.tenant_id == tenant_id,
            )
        )
        db_r = result.scalar_one_or_none()
        return _return_to_domain(db_r) if db_r else None

    async def update_status(
        self, return_id: uuid.UUID, tenant_id: str, status: ReturnStatus
    ) -> ReturnTransaction | None:
        db_r = await self._session.get(db_models.ReturnTransaction, return_id)
        if db_r is None or db_r.tenant_id != tenant_id:
            return None
        db_r.status = status.value
        await self._session.flush()
        await self._session.refresh(db_r)
        return _return_to_domain(db_r)
