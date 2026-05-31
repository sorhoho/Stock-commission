from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.domain.models import AgreementSpec, AgreementSpecCreate, AgreementSpecUpdate
from app.infrastructure.db.models import AgreementSpec as AgreementSpecORM
from app.infrastructure.db.repository import AgreementSpecRepository
from telco_common.auth import require_auth
from telco_common.auth.scopes import Scopes
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/agreementSpec", tags=["Agreement Specs"])


@router.get("/", response_model=list[AgreementSpec])
async def list_agreement_specs(
    db: AsyncSession = Depends(get_db),
    token=Depends(require_auth([Scopes.COMMISSION_RULES_READ])),
):
    repo = AgreementSpecRepository(db)
    return [AgreementSpec.model_validate(s) for s in await repo.list_active(token.tenant_id)]


@router.post("/", response_model=AgreementSpec, status_code=201)
async def create_agreement_spec(
    data: AgreementSpecCreate,
    db: AsyncSession = Depends(get_db),
    _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE])),
):
    repo = AgreementSpecRepository(db)
    spec = AgreementSpecORM(**data.model_dump())
    return AgreementSpec.model_validate(await repo.create(spec))


@router.get("/{spec_id}", response_model=AgreementSpec)
async def get_agreement_spec(spec_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_READ]))):
    repo = AgreementSpecRepository(db)
    item = await repo.get_by_id(str(spec_id))
    if not item:
        raise NotFoundException("AgreementSpec", str(spec_id))
    return AgreementSpec.model_validate(item)


@router.patch("/{spec_id}", response_model=AgreementSpec)
async def update_agreement_spec(spec_id: uuid.UUID, data: AgreementSpecUpdate, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    repo = AgreementSpecRepository(db)
    updated = await repo.update(str(spec_id), data.model_dump(exclude_none=True))
    if not updated:
        raise NotFoundException("AgreementSpec", str(spec_id))
    return AgreementSpec.model_validate(updated)


@router.delete("/{spec_id}", status_code=204)
async def delete_agreement_spec(spec_id: uuid.UUID, db: AsyncSession = Depends(get_db), _token=Depends(require_auth([Scopes.COMMISSION_RULES_WRITE]))):
    await AgreementSpecRepository(db).soft_delete(str(spec_id))
