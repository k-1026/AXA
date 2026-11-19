"""사후관리 규칙 (B).

- 환자 쪽(`patient_open`, `patient_post`)은 A의 환자 라우터가 부른다 (contracts 5절에 추가 제안)
- 병원 쪽(`tenant_*`)은 `aftercare/router_tenant.py`(B)가 부른다. tenant_id로만 조회 → 남의 병원 대화는 404
- 사후관리를 지원하는 병원(`tenants.aftercare_enabled`)의 방문 완료(`visited`) 요청서만 대화를 열 수 있음
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from modules.aftercare.models import THREAD_STATUSES, AftercareMessage, AftercareThread
from modules.booking.models import BookingRequest
from modules.tenant.models import Tenant


def _not_found() -> AppError:
    return AppError(404, "not_found", "사후관리 대화를 찾을 수 없습니다")


def _add(db: Session, thread: AftercareThread, sender: str, text: str, *, staff_id=None, translated=None, photo=False):
    text = (text or "").strip()
    if not text:
        raise AppError(422, "validation", "내용을 입력하세요", {"errors": [{"loc": ["text"], "type": "missing"}]})
    msg = AftercareMessage(
        thread_id=thread.id, sender=sender, staff_id=staff_id, text_original=text[:4000],
        text_translated=translated, has_photo=photo,
    )
    db.add(msg)
    thread.last_message_at = utcnow()
    return msg


# ---------- 환자 쪽 (A가 호출) ----------


def patient_open(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID, text: str, photo: bool = False) -> AftercareThread:
    req = db.get(BookingRequest, request_id)
    if req is None or req.patient_id != patient_id:
        raise _not_found()
    tenant = db.get(Tenant, req.tenant_id)
    if req.status != "visited" or tenant is None or not tenant.aftercare_enabled:
        # 방문 전이거나 사후관리 미지원 병원 → 환자 화면에서는 "병원에 직접 연락" 안내
        raise AppError(409, "booking.invalid_transition", "사후관리 대화를 열 수 없습니다", {"status": req.status})
    thread = db.scalar(select(AftercareThread).where(AftercareThread.request_id == request_id))
    if thread is None:
        thread = AftercareThread(request_id=request_id, tenant_id=req.tenant_id)
        db.add(thread)
        db.flush()
    else:
        thread.status = "new" if thread.status == "resolved" else thread.status
    _add(db, thread, "patient", text, photo=photo)
    db.commit()
    db.refresh(thread)
    return thread


# ---------- 병원 쪽 (B) ----------


def tenant_get(db: Session, tenant_id: uuid.UUID, thread_id: uuid.UUID) -> AftercareThread:
    t = db.get(AftercareThread, thread_id)
    if t is None or t.tenant_id != tenant_id:
        raise _not_found()
    return t


def tenant_list(db: Session, tenant_id: uuid.UUID, status: str | None = None) -> list[dict]:
    q = (
        select(AftercareThread, BookingRequest)
        .join(BookingRequest, BookingRequest.id == AftercareThread.request_id)
        .where(AftercareThread.tenant_id == tenant_id)
    )
    if status:
        q = q.where(AftercareThread.status == status)
    rows = db.execute(q.order_by(AftercareThread.last_message_at.desc())).all()
    out = []
    for thread, req in rows:
        last = db.scalar(
            select(AftercareMessage).where(AftercareMessage.thread_id == thread.id).order_by(AftercareMessage.id.desc()).limit(1)
        )
        unread = db.scalar(
            select(func.count()).select_from(AftercareMessage).where(
                AftercareMessage.thread_id == thread.id,
                AftercareMessage.sender == "patient",
                AftercareMessage.id > (
                    select(func.coalesce(func.max(AftercareMessage.id), 0))
                    .where(AftercareMessage.thread_id == thread.id, AftercareMessage.sender == "staff")
                    .scalar_subquery()
                ),
            )
        )
        out.append({"thread": thread, "request": req, "last": last, "unanswered": unread or 0})
    return out


def tenant_messages(db: Session, tenant_id: uuid.UUID, thread_id: uuid.UUID) -> tuple[AftercareThread, BookingRequest, list]:
    thread = tenant_get(db, tenant_id, thread_id)
    req = db.get(BookingRequest, thread.request_id)
    msgs = list(db.scalars(select(AftercareMessage).where(AftercareMessage.thread_id == thread.id).order_by(AftercareMessage.id)))
    return thread, req, msgs


def tenant_reply(db: Session, tenant_id: uuid.UUID, staff_id: str, thread_id: uuid.UUID, text: str) -> AftercareThread:
    thread = tenant_get(db, tenant_id, thread_id)
    try:
        sid = uuid.UUID(staff_id)
    except ValueError:
        sid = None
    _add(db, thread, "staff", text, staff_id=sid)
    if thread.status == "new":
        thread.status = "in_progress"
    db.commit()
    db.refresh(thread)
    return thread


def tenant_update(db: Session, tenant_id: uuid.UUID, thread_id: uuid.UUID, status: str | None, tags: list[str] | None) -> AftercareThread:
    thread = tenant_get(db, tenant_id, thread_id)
    if status is not None:
        if status not in THREAD_STATUSES:
            raise AppError(422, "validation", "상태 코드가 올바르지 않습니다", {"errors": [{"loc": ["status"], "type": "enum"}]})
        thread.status = status
        thread.resolved_at = utcnow() if status == "resolved" else None
    if tags is not None:
        thread.tags = [t.strip()[:30] for t in tags if t.strip()][:10]
    db.commit()
    db.refresh(thread)
    return thread
