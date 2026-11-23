"""환자 알림 API (A, contracts 6-5, 결정 27). 모두 환자 로그인 필요, 자기 알림만."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import get_db
from core.security import PatientPrincipal, current_patient, patient_uuid
from modules.notification import service

router = APIRouter(prefix="/me/notifications", tags=["notification"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


class NotificationOut(BaseModel):
    id: int
    kind: str  # status · reply · aftercare
    request_id: str
    hospital_id: int | None  # 화면에서 병원 이름을 찾는 데 씀
    status: str | None
    created_at: datetime
    read: bool


class ReadIn(BaseModel):
    ids: list[int] | None = Field(default=None, max_length=200)  # 비우면 모두 읽음


class RealtimeOut(BaseModel):
    url: str  # Supabase 프로젝트 주소
    token: str  # Realtime 접속 토큰 (1시간)
    expires_at: datetime


@router.get("", response_model=list[NotificationOut])
def list_mine(db: Db, me: Me):
    return [
        NotificationOut(id=n.id, kind=n.kind, request_id=str(n.request_id), hospital_id=h, status=n.status,
                        created_at=n.created_at, read=n.read_at is not None)
        for n, h in service.list_mine(db, patient_uuid(me))
    ]


@router.post("/read")
def read(body: ReadIn, db: Db, me: Me) -> dict[str, int]:
    return {"updated": service.mark_read(db, patient_uuid(me), body.ids)}


@router.post("/realtime-token", response_model=RealtimeOut)
def realtime_token(me: Me):
    token, exp = service.realtime_token(patient_uuid(me))
    return RealtimeOut(url=get_settings().supabase_url, token=token, expires_at=exp)
