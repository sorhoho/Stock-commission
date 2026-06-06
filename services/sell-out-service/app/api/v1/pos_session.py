"""POS Session API — shift/till management for retail outlets."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_tenant_id
from app.domain.models import PosSession, PosSessionClose, PosSessionCreate, PosSessionStatus
from app.infrastructure.db.repository import PosSessionRepository
from app.infrastructure.db.session import get_db_session
from telco_common.exceptions import NotFoundException, UnprocessableEntityException

router = APIRouter(prefix="/posSession", tags=["POS Session"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
TenantId = Annotated[str, Depends(get_tenant_id)]


@router.post("/", response_model=PosSession, status_code=status.HTTP_201_CREATED)
async def open_session(body: PosSessionCreate, tenant_id: TenantId, db: DbSession) -> PosSession:
    """Open a new POS session (shift open)."""
    repo = PosSessionRepository(db)
    return await repo.create(body, tenant_id)


@router.get("/{session_id}", response_model=PosSession)
async def get_session(session_id: uuid.UUID, tenant_id: TenantId, db: DbSession) -> PosSession:
    repo = PosSessionRepository(db)
    session = await repo.get_by_id(session_id, tenant_id)
    if session is None:
        raise NotFoundException("PosSession", str(session_id))
    return session


@router.post("/{session_id}/close", response_model=PosSession)
async def close_session(
    session_id: uuid.UUID, body: PosSessionClose, tenant_id: TenantId, db: DbSession
) -> PosSession:
    """Close an open POS session (shift close)."""
    repo = PosSessionRepository(db)
    session = await repo.get_by_id(session_id, tenant_id)
    if session is None:
        raise NotFoundException("PosSession", str(session_id))
    if session.status != PosSessionStatus.OPEN:
        raise UnprocessableEntityException(f"Session is already {session.status}")
    updated = await repo.close(session_id, tenant_id, body.closing_cash)
    return updated
