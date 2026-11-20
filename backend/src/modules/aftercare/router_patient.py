"""환자용 사후관리 API (A). 규칙은 aftercare.service(B)에 있음 (contracts 6-3).

- `GET /me/aftercare`: 내 사후관리 대화 목록 (최근 메시지 순)
- `GET /me/booking-requests/{id}/aftercare`: 요청서 1건의 대화 (아직 없으면 404 → 화면은 빈 대화)
- `POST /me/booking-requests/{id}/aftercare/messages`: 보내기. 첫 메시지면 대화를 엶 (방문 완료 + 사후관리 지원 병원만, 아니면 409)
- `POST /me/booking-requests/{id}/aftercare/uploads`: 사진·영상 1개의 업로드 주소 (Supabase Storage, 브라우저가 바로 PUT) → 보낼 때 `attachments`에 경로
- 저장소 설정이 없으면 업로드는 503 `storage.unavailable` → 화면은 예전처럼 `photo: true`("사진 있음")만 보냄
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import PatientPrincipal, current_patient, patient_uuid
from core.errors import AppError
from modules.aftercare import service
from modules.media import service as media

router = APIRouter(tags=["aftercare"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


class AttachmentOut(BaseModel):
    kind: str  # image / video
    name: str | None
    url: str | None = None  # 1시간짜리 서명된 주소. 못 만들면 None ("사진 있음"만 표시)


class PatientMessageOut(BaseModel):
    id: int
    sender: str  # patient / staff
    text_original: str
    text_translated: str | None  # 번역은 ai/llm 연결 뒤 (지금은 비어 있음 → 원문 표시)
    has_photo: bool
    attachments: list[AttachmentOut] = []
    created_at: datetime


class PatientThreadOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    status: str
    last_message_at: datetime
    last_message: str | None = None
    unread: int = 0  # 내가 마지막으로 보낸 뒤 병원이 보낸 수
    messages: list[PatientMessageOut] | None = None


class AttachmentIn(BaseModel):
    path: str = Field(max_length=300)  # 업로드 API가 준 경로 (이 요청서 경로만 허용)
    kind: Literal["image", "video"]
    name: str = Field(default="", max_length=200)


class PatientMessageIn(BaseModel):
    text: str = Field(max_length=4000)
    photo: bool = False
    attachments: list[AttachmentIn] = Field(default=[], max_length=4)


class UploadIn(BaseModel):
    name: str = Field(default="", max_length=200)
    content_type: str = Field(max_length=100)
    size: int = Field(gt=0)


class UploadOut(BaseModel):
    path: str
    kind: str
    upload_url: str  # 이 주소로 파일을 PUT (Content-Type = content_type), 2시간 안에 한 번


def _out(thread, msgs=None, last=None, unread=0) -> PatientThreadOut:
    files = media.attachments_out(msgs) if msgs else {}
    return PatientThreadOut(
        id=thread.id, request_id=thread.request_id, status=thread.status, last_message_at=thread.last_message_at,
        last_message=last.text_original if last else None, unread=unread,
        messages=[
            PatientMessageOut.model_validate(m, from_attributes=True).model_copy(
                update={"attachments": [AttachmentOut(**a) for a in files.get(m.id, [])]}
            )
            for m in msgs
        ] if msgs is not None else None,
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
    service.patient_open(db, pid, request_id, body.text, photo=body.photo,
                         attachments=[a.model_dump() for a in body.attachments])
    thread, msgs = service.patient_messages(db, pid, request_id)
    return _out(thread, msgs)


@router.post("/me/booking-requests/{request_id}/aftercare/uploads", response_model=UploadOut, status_code=201)
def upload_url(request_id: uuid.UUID, body: UploadIn, db: Db, me: Me):
    kind = media.kind_of(body.content_type)
    if kind is None or body.size > media.MAX_BYTES:
        loc = "content_type" if kind is None else "size"
        raise AppError(422, "validation", "사진·영상만, 1개 50MB까지 올릴 수 있습니다", {"errors": [{"loc": [loc], "type": "invalid"}]})
    prefix = service.patient_upload_prefix(db, patient_uuid(me), request_id)  # 404·409 먼저
    path = media.new_path(prefix, body.name)
    return UploadOut(path=path, kind=kind, upload_url=media.sign_upload(path))
