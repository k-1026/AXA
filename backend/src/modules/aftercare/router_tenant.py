"""병원용 사후관리 API (B). 모든 경로는 직원 토큰의 tenant_id로만 조회."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import StaffPrincipal, current_staff
from modules.aftercare import service
from modules.audit import service as audit
from modules.media import service as media

router = APIRouter(prefix="/tenant/aftercare", tags=["tenant"])

Db = Annotated[Session, Depends(get_db)]
Staff = Annotated[StaffPrincipal, Depends(current_staff)]


class MessageOut(BaseModel):
    id: int
    sender: str
    text_original: str
    text_translated: str | None
    has_photo: bool
    attachments: list[dict] = []  # [{kind, name, url(1시간)}] — A 추가 (Storage, B 확인)
    created_at: datetime


class ThreadOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    status: str
    tags: list[str]
    summary: str | None
    lang: str
    nationality: str
    treatment: str | None
    visited_slot: datetime | None
    last_message_at: datetime
    last_message: str | None = None
    unanswered: int = 0
    messages: list[MessageOut] | None = None


class ReplyIn(BaseModel):
    text: str


class ThreadUpdate(BaseModel):
    status: str | None = None
    tags: list[str] | None = None


def _tenant(staff: StaffPrincipal) -> uuid.UUID:
    try:
        return uuid.UUID(staff.tenant_id)
    except ValueError:
        raise AppError(401, "auth.required", "로그인이 필요합니다")


def _messages(messages) -> list[MessageOut]:
    files = media.attachments_out(messages)
    return [MessageOut.model_validate(m, from_attributes=True).model_copy(update={"attachments": files.get(m.id, [])})
            for m in messages]


def _out(thread, req, last=None, unanswered=0, messages=None) -> ThreadOut:
    return ThreadOut(
        id=thread.id, request_id=thread.request_id, status=thread.status, tags=thread.tags or [],
        summary=thread.summary, lang=req.lang, nationality=req.nationality, treatment=req.treatment,
        visited_slot=req.confirmed_slot, last_message_at=thread.last_message_at,
        last_message=last.text_original if last else None, unanswered=unanswered,
        messages=_messages(messages) if messages is not None else None,
    )


@router.get("", response_model=list[ThreadOut])
def list_threads(db: Db, staff: Staff, status: str | None = None):
    return [_out(r["thread"], r["request"], r["last"], r["unanswered"]) for r in service.tenant_list(db, _tenant(staff), status)]


@router.get("/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: uuid.UUID, db: Db, staff: Staff):
    thread, req, msgs = service.tenant_messages(db, _tenant(staff), thread_id)
    audit.log_and_commit(db, _tenant(staff), staff.staff_id, "aftercare.view", f"aftercare_thread:{thread_id}")
    return _out(thread, req, messages=msgs)


@router.post("/{thread_id}/messages", response_model=ThreadOut)
def reply(thread_id: uuid.UUID, data: ReplyIn, db: Db, staff: Staff):
    service.tenant_reply(db, _tenant(staff), staff.staff_id, thread_id, data.text)
    thread, req, msgs = service.tenant_messages(db, _tenant(staff), thread_id)
    audit.log_and_commit(db, _tenant(staff), staff.staff_id, "aftercare.reply", f"aftercare_thread:{thread_id}")
    return _out(thread, req, messages=msgs)


@router.patch("/{thread_id}", response_model=ThreadOut)
def update_thread(thread_id: uuid.UUID, data: ThreadUpdate, db: Db, staff: Staff):
    service.tenant_update(db, _tenant(staff), thread_id, data.status, data.tags)
    thread, req, msgs = service.tenant_messages(db, _tenant(staff), thread_id)
    return _out(thread, req, messages=msgs)
