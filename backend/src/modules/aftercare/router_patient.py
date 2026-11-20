"""환자용 사후관리 API (A). 규칙은 aftercare.service(B)에 있음 (contracts 6-3).

- `GET /me/aftercare`: 내 사후관리 대화 목록 (최근 메시지 순)
- `GET /me/booking-requests/{id}/aftercare`: 요청서 1건의 대화 (아직 없으면 404 → 화면은 빈 대화)
- `POST /me/booking-requests/{id}/aftercare/messages`: 보내기. 첫 메시지면 대화를 엶 (방문 완료 + 사후관리 지원 병원만, 아니면 409)
- 사진·영상 파일은 아직 저장하지 않음 → `photo: true`면 "사진 있음" 표시만
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import PatientPrincipal, current_patient, patient_uuid
from modules.aftercare import service

router = APIRouter(tags=["aftercare"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


class PatientMessageOut(BaseModel):
    id: int
    sender: str  # patient / staff
    text_original: str
    text_translated: str | None  # 번역은 ai/llm 연결 뒤 (지금은 비어 있음 → 원문 표시)
    has_photo: bool
    created_at: datetime


class PatientThreadOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    status: str
    last_message_at: datetime
    last_message: str | None = None
    unread: int = 0  # 내가 마지막으로 보낸 뒤 병원이 보낸 수
    messages: list[PatientMessageOut] | None = None


class PatientMessageIn(BaseModel):
    text: str = Field(max_length=4000)
    photo: bool = False


def _out(thread, msgs=None, last=None, unread=0) -> PatientThreadOut:
    return PatientThreadOut(
        id=thread.id, request_id=thread.request_id, status=thread.status, last_message_at=thread.last_message_at,
        last_message=last.text_original if last else None, unread=unread,
        messages=[PatientMessageOut.model_validate(m, from_attributes=True) for m in msgs] if msgs is not None else None,
    )


@router.get("/me/aftercare", response_model=list[PatientThreadOut])
def list_mine(db: Db, me: Me):
    return [_out(r["thread"], last=r["last"], unread=r["unread"]) for r in service.patient_list(db, patient_uuid(me))]


@router.get("/me/booking-requests/{request_id}/aftercare", response_model=PatientThreadOut)
def get_mine(request_id: uuid.UUID, db: Db, me: Me):
    thread, msgs = service.patient_messages(db, patient_uuid(me), request_id)
    return _out(thread, msgs)


@router.post("/me/booking-requests/{request_id}/aftercare/messages", response_model=PatientThreadOut, status_code=201)
def send(request_id: uuid.UUID, body: PatientMessageIn, db: Db, me: Me):
    pid = patient_uuid(me)
    service.patient_open(db, pid, request_id, body.text, photo=body.photo)
    thread, msgs = service.patient_messages(db, pid, request_id)
    return _out(thread, msgs)
