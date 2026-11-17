"""병원 계정 API (B). 대시보드 머리말·사후관리 지원 스위치."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import StaffPrincipal, current_staff
from modules.tenant.models import Tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])

Db = Annotated[Session, Depends(get_db)]
Staff = Annotated[StaffPrincipal, Depends(current_staff)]


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hospital_id: int
    display_name: str
    registration_no: str | None
    requests_enabled: bool
    aftercare_enabled: bool


class TenantUpdate(BaseModel):
    aftercare_enabled: bool | None = None


def get_tenant(db: Session, staff: StaffPrincipal) -> Tenant:
    try:
        tenant = db.get(Tenant, uuid.UUID(staff.tenant_id))
    except ValueError:
        tenant = None
    if tenant is None:
        raise AppError(401, "auth.required", "로그인이 필요합니다")
    return tenant


@router.get("/me", response_model=TenantOut)
def get_me(db: Db, staff: Staff):
    return get_tenant(db, staff)


@router.patch("/me", response_model=TenantOut)
def update_me(data: TenantUpdate, db: Db, staff: Staff):
    """사후관리 지원 켜기·끄기. 끄면 환자 사이트 '사후관리 지원' 필터에서 빠지고 새 사후관리 문의를 받지 않음
    (이미 있는 대화는 병원이 계속 볼 수 있음)."""
    tenant = get_tenant(db, staff)
    if data.aftercare_enabled is not None:
        tenant.aftercare_enabled = data.aftercare_enabled
    db.commit()
    db.refresh(tenant)
    return tenant
