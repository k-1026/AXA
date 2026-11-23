"""병원용 열람·처리 기록 조회 (B 모듈, A 작성 · B 확인). 자기 병원 기록만, 최근 순."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import StaffPrincipal, current_staff
from modules.audit import service

router = APIRouter(prefix="/tenant", tags=["tenant"])


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor: str
    action: str
    ref: str
    created_at: datetime


@router.get("/audit-logs", response_model=list[AuditOut])
def list_logs(
    db: Annotated[Session, Depends(get_db)],
    staff: Annotated[StaffPrincipal, Depends(current_staff)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    try:
        tenant = uuid.UUID(staff.tenant_id)
    except ValueError:
        raise AppError(401, "auth.required", "로그인이 필요합니다")
    return service.recent(db, tenant, limit)
