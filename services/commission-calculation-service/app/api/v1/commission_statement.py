"""Commission statement endpoints — TMF666."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.models import CommissionStatement, CommissionStatementStatus
from app.infrastructure.db.repository import CommissionStatementRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import ConflictException, NotFoundException

router = APIRouter(prefix="/commissionStatement", tags=["Commission Statements"])


@router.get("/", response_model=list[CommissionStatement])
async def list_statements(
    party_id: UUID | None = None,
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_READ])),
):
    repo = CommissionStatementRepository(db)
    items, _ = await repo.list_with_filters(
        tenant_id=token.tenant_id,
        party_id=party_id,
        year=year,
        month=month,
    )
    return [CommissionStatement.model_validate(i) for i in items]


@router.get("/{statement_id}", response_model=CommissionStatement)
async def get_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_READ])),
):
    repo = CommissionStatementRepository(db)
    item = await repo.get_by_id(statement_id, token.tenant_id)
    if not item:
        raise NotFoundException("CommissionStatement", str(statement_id))
    return CommissionStatement.model_validate(item)


@router.post("/{statement_id}/confirm", response_model=CommissionStatement)
async def confirm_statement(
    statement_id: UUID,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_CONFIRM])),
):
    repo = CommissionStatementRepository(db)
    item = await repo.get_by_id(statement_id, token.tenant_id)
    if not item:
        raise NotFoundException("CommissionStatement", str(statement_id))
    if item.status != CommissionStatementStatus.DRAFT:
        raise ConflictException(f"Statement {statement_id} is already {item.status}")
    confirmed = await repo.confirm(str(statement_id))
    return CommissionStatement.model_validate(confirmed)


@router.post("/{statement_id}/dispute", response_model=dict)
async def dispute_statement(
    statement_id: UUID,
    body: dict = Body(..., example={"reason": "Incorrect commission rate applied"}),
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_STATEMENT_READ])),
):
    repo = CommissionStatementRepository(db)
    item = await repo.get_by_id(statement_id, token.tenant_id)
    if not item:
        raise NotFoundException("CommissionStatement", str(statement_id))
    return {"status": "dispute_received", "statement_id": str(statement_id), "reason": body.get("reason")}
