from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.models import Agreement, AgreementCreate, AgreementUpdate, AgreementWithRules
from app.infrastructure.db.models import Agreement as AgreementORM
from app.infrastructure.db.repository import AgreementRepository, CommissionRuleRepository
from app.domain.models import CommissionRule
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/agreement", tags=["Agreements"])


@router.get("/", response_model=list[Agreement])
async def list_agreements(
    party_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_RULES_READ])),
):
    repo = AgreementRepository(db)
    items = await repo.list_with_filters(token.tenant_id, party_id=str(party_id) if party_id else None, status=status)
    return [Agreement.model_validate(i) for i in items]


@router.post("/", response_model=Agreement, status_code=201)
async def create_agreement(data: AgreementCreate, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    repo = AgreementRepository(db)
    agreement = AgreementORM(**data.model_dump())
    return Agreement.model_validate(await repo.create(agreement))


@router.get("/party/{party_id}/active", response_model=AgreementWithRules)
async def get_active_agreement_for_party(
    party_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_RULES_READ])),
):
    """Key endpoint called by commission-calculation-service."""
    agreement_repo = AgreementRepository(db)
    rule_repo = CommissionRuleRepository(db)

    agreement = await agreement_repo.get_active_for_party(str(party_id), token.tenant_id)
    if not agreement:
        raise NotFoundException("Agreement", f"party/{party_id}/active")

    rules = await rule_repo.list_for_spec(str(agreement.agreement_spec_id))
    return AgreementWithRules(
        id=str(agreement.id),
        agreement_spec_id=str(agreement.agreement_spec_id),
        party_id=str(agreement.party_id),
        party_name=agreement.party_name,
        status=agreement.status,
        rules=[CommissionRule.model_validate(r) for r in rules],
    )


@router.get("/{agreement_id}", response_model=Agreement)
async def get_agreement(agreement_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_READ]))):
    repo = AgreementRepository(db)
    item = await repo.get_by_id(str(agreement_id))
    if not item:
        raise NotFoundException("Agreement", str(agreement_id))
    return Agreement.model_validate(item)


@router.patch("/{agreement_id}", response_model=Agreement)
async def update_agreement(agreement_id: uuid.UUID, data: AgreementUpdate, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    repo = AgreementRepository(db)
    if data.status:
        await repo.update_status(str(agreement_id), data.status)
    item = await repo.get_by_id(str(agreement_id))
    if not item:
        raise NotFoundException("Agreement", str(agreement_id))
    return Agreement.model_validate(item)
