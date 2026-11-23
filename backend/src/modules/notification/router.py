"""환자 알림 API (A, contracts 6-5, 결정 27). 모두 환자 로그인 필요, 자기 알림만."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import get_db
from core.security import PatientPrincipal, current_patient, patient_uuid
from modules.notification import push, service

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


# ---------- 웹 푸시 (결정 30) ----------

push_router = APIRouter(prefix="/me/push", tags=["notification"])


class PushKeyOut(BaseModel):
    public_key: str  # VAPID 공개 키 (base64url) → pushManager.subscribe의 applicationServerKey


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(pattern=r"^https://", max_length=1000)  # 브라우저 푸시 서비스 주소
    keys: PushKeys


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1000)


@push_router.get("/key", response_model=PushKeyOut)
def push_key(me: Me):
    return PushKeyOut(public_key=push.public_key())


@push_router.post("/subscriptions", status_code=204)
def push_subscribe(body: PushSubscriptionIn, db: Db, me: Me):
    push.public_key()  # 꺼진 서버면 503 (저장해도 보낼 수 없음)
    push.subscribe(db, patient_uuid(me), body.endpoint, body.keys.p256dh, body.keys.auth)


@push_router.delete("/subscriptions", status_code=204)
def push_unsubscribe(body: PushUnsubscribeIn, db: Db, me: Me):
    push.unsubscribe(db, patient_uuid(me), body.endpoint)
