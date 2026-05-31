from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_kafka_producer
from app.domain.models import PayoutRequest, PayoutRequestCreate
from app.domain.services import create_payout_request, process_payout
from app.infrastructure.db.repository import PayoutRequestRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/payoutRequest", tags=["Payout Requests"])


@router.get("/", response_model=list[PayoutRequest])
async def list_payout_requests(
    party_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.PAYOUT_CREATE])),
):
    repo = PayoutRequestRepository(db)
    items = await repo.list_with_filters(token.tenant_id, party_id=str(party_id) if party_id else None, status=status)
    return [PayoutRequest.model_validate(i) for i in items]


@router.post("/", response_model=PayoutRequest, status_code=201)
async def create_request(
    data: PayoutRequestCreate,
    db: AsyncSession = Depends(get_db),
    kafka_producer=Depends(get_kafka_producer),
    _token=Depends(require_auth([Scopes.PAYOUT_ADMIN])),
):
    repo = PayoutRequestRepository(db)
    result = await create_payout_request(
        party_id=str(data.party_id),
        statement_id=str(data.statement_id),
        amount=data.amount,
        currency=data.currency,
        payment_method=data.payment_method,
        bank_account_ref=data.bank_account_ref,
        scheduled_date=data.scheduled_date,
        tenant_id=data.tenant_id,
        repo=repo,
        kafka_producer=kafka_producer,
    )
    return PayoutRequest.model_validate(result)


@router.get("/{request_id}", response_model=PayoutRequest)
async def get_request(request_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.PAYOUT_CREATE]))):
    repo = PayoutRequestRepository(db)
    item = await repo.get_by_id(str(request_id))
    if not item:
        raise NotFoundException("PayoutRequest", str(request_id))
    return PayoutRequest.model_validate(item)


@router.post("/{request_id}/process", response_model=PayoutRequest)
async def process_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kafka_producer=Depends(get_kafka_producer),
    token=Depends(require_auth([Scopes.PAYOUT_ADMIN])),
):
    repo = PayoutRequestRepository(db)
    return PayoutRequest.model_validate(await process_payout(str(request_id), token.tenant_id, repo, kafka_producer))


@router.get("/{request_id}/receipt")
async def get_receipt(request_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.PAYOUT_CREATE]))):
    repo = PayoutRequestRepository(db)
    item = await repo.get_by_id(str(request_id))
    if not item:
        raise NotFoundException("PayoutRequest", str(request_id))
    return {
        "receipt_number": f"RCP-{str(request_id)[:8].upper()}",
        "payout_id": str(item.id),
        "party_id": str(item.party_id),
        "amount": item.amount,
        "currency": item.currency,
        "status": item.status,
        "processed_date": item.processed_date,
        "external_reference": item.external_reference,
    }
