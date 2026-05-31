from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.models import CommissionRule, CommissionRuleCreate, CommissionRuleUpdate
from app.infrastructure.db.models import CommissionRule as CommissionRuleORM
from app.infrastructure.db.repository import CommissionRuleRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/commissionRule", tags=["Commission Rules"])


@router.get("/", response_model=list[CommissionRule])
async def list_rules(agreement_spec_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_READ]))):
    repo = CommissionRuleRepository(db)
    if agreement_spec_id:
        items = await repo.list_for_spec(str(agreement_spec_id))
    else:
        from sqlalchemy import select
        result = await db.execute(select(CommissionRuleORM).where(~CommissionRuleORM.is_deleted))
        items = list(result.scalars())
    return [CommissionRule.model_validate(i) for i in items]


@router.post("/", response_model=CommissionRule, status_code=201)
async def create_rule(data: CommissionRuleCreate, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    repo = CommissionRuleRepository(db)
    rule = CommissionRuleORM(**data.model_dump())
    return CommissionRule.model_validate(await repo.create(rule))


@router.get("/{rule_id}", response_model=CommissionRule)
async def get_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_READ]))):
    repo = CommissionRuleRepository(db)
    item = await repo.get_by_id(str(rule_id))
    if not item:
        raise NotFoundException("CommissionRule", str(rule_id))
    return CommissionRule.model_validate(item)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    await CommissionRuleRepository(db).soft_delete(str(rule_id))
