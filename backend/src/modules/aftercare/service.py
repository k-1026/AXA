"""사후관리 규칙 (B).

- 환자 쪽(`patient_open`, `patient_list`, `patient_messages`)은 A의 `aftercare/router_patient.py`가 부른다 (contracts 6-3, 조회 함수 2개는 A가 추가 · B 확인 필요)
- 병원 쪽(`tenant_*`)은 `aftercare/router_tenant.py`(B)가 부른다. tenant_id로만 조회 → 남의 병원 대화는 404
- 사후관리를 지원하는 병원(`tenants.aftercare_enabled`)의 방문 완료(`visited`) 요청서만 대화를 열 수 있음
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from modules.agent import translate
from modules.notification import service as notification
from modules.aftercare.models import THREAD_STATUSES, AftercareMessage, AftercareThread
from modules.booking.models import BookingRequest
from modules.tenant.models import Tenant


def _not_found() -> AppError:
    return AppError(404, "not_found", "사후관리 대화를 찾을 수 없습니다")


def _add(db: Session, thread: AftercareThread, sender: str, text: str, *, staff_id=None, translated=None, photo=False,
         attachments: list[dict] | None = None):
    text = (text or "").strip()
    if not text:
        raise AppError(422, "validation", "내용을 입력하세요", {"errors": [{"loc": ["text"], "type": "missing"}]})
    msg = AftercareMessage(
        thread_id=thread.id, sender=sender, staff_id=staff_id, text_original=text[:4000],
        text_translated=translated, has_photo=photo or bool(attachments), attachments=attachments or [],
    )
    db.add(msg)
    thread.last_message_at = utcnow()
    return msg


# ---------- 환자 쪽 (A가 호출) ----------


def _openable(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID) -> BookingRequest:
    req = db.get(BookingRequest, request_id)
    if req is None or req.patient_id != patient_id:
        raise _not_found()
    tenant = db.get(Tenant, req.tenant_id)
    if req.status not in ("visited", "paid") or tenant is None or not tenant.aftercare_enabled:  # 결제 확인 뒤에도 사후관리
        # 방문 전이거나 사후관리 미지원 병원 → 환자 화면에서는 "병원에 직접 연락" 안내
        raise AppError(409, "booking.invalid_transition", "사후관리 대화를 열 수 없습니다", {"status": req.status})
    return req


def media_prefix(req: BookingRequest) -> str:
    """첨부 파일 경로 앞부분 `{tenant_id}/{request_id}` — 다른 대화의 파일을 붙이지 못하게 이 앞부분만 허용."""
    return f"{req.tenant_id}/{req.id}"


def patient_upload_prefix(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID) -> str:
    """사진·영상을 올려도 되는지 (대화를 열 수 있는 요청서인지) 확인하고 경로 앞부분을 줌. A가 추가 (B 확인)."""
    return media_prefix(_openable(db, patient_id, request_id))


def patient_open(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID, text: str, photo: bool = False,
                 attachments: list[dict] | None = None) -> AftercareThread:
    req = _openable(db, patient_id, request_id)
    prefix = media_prefix(req) + "/"
    if any(not str(a.get("path", "")).startswith(prefix) for a in attachments or []):
        raise AppError(422, "validation", "첨부 파일이 올바르지 않습니다", {"errors": [{"loc": ["attachments"], "type": "path"}]})
    thread = db.scalar(select(AftercareThread).where(AftercareThread.request_id == request_id))
    if thread is None:
        thread = AftercareThread(request_id=request_id, tenant_id=req.tenant_id)
        db.add(thread)
        db.flush()
    else:
        thread.status = "new" if thread.status == "resolved" else thread.status
    # 병원 직원용 한국어 번역 (요청서 번역 동의가 있을 때만, 실패하면 원문만 — 결정 25)
    ko = translate.for_request(db, req.id, text, "ko", req.tenant_id)
    _add(db, thread, "patient", text, photo=photo, attachments=attachments, translated=ko)
    notification.notify_staff(db, req.tenant_id, "aftercare", req.id)  # 병원 대시보드에 바로 (11/27)
    db.commit()
    db.refresh(thread)
    return thread


def _unanswered_by(db: Session, thread_id: uuid.UUID, sender: str, other: str) -> int:
    """`other`가 마지막으로 보낸 뒤 `sender`가 보낸 메시지 수 (환자 화면 = 안 읽은 병원 답장 수)."""
    return db.scalar(
        select(func.count()).select_from(AftercareMessage).where(
            AftercareMessage.thread_id == thread_id,
            AftercareMessage.sender == sender,
            AftercareMessage.id > (
                select(func.coalesce(func.max(AftercareMessage.id), 0))
                .where(AftercareMessage.thread_id == thread_id, AftercareMessage.sender == other)
                .scalar_subquery()
            ),
        )
    ) or 0


def patient_list(db: Session, patient_id: uuid.UUID) -> list[dict]:
    """내 사후관리 대화 (최근 메시지 순). 남의 요청서 대화는 나오지 않음."""
    rows = db.execute(
        select(AftercareThread, BookingRequest)
        .join(BookingRequest, BookingRequest.id == AftercareThread.request_id)
        .where(BookingRequest.patient_id == patient_id)
        .order_by(AftercareThread.last_message_at.desc())
    ).all()
    out = []
    for thread, req in rows:
        last = db.scalar(
            select(AftercareMessage).where(AftercareMessage.thread_id == thread.id).order_by(AftercareMessage.id.desc()).limit(1)
        )
        out.append({"thread": thread, "request": req, "last": last, "unread": _unanswered_by(db, thread.id, "staff", "patient")})
    return out


def patient_messages(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID) -> tuple[AftercareThread, list]:
    """요청서 1건의 대화와 메시지. 대화가 아직 없거나 남의 요청서면 404."""
    req = db.get(BookingRequest, request_id)
    thread = db.scalar(select(AftercareThread).where(AftercareThread.request_id == request_id)) if req else None
    if req is None or req.patient_id != patient_id or thread is None:
        raise _not_found()
    msgs = list(db.scalars(select(AftercareMessage).where(AftercareMessage.thread_id == thread.id).order_by(AftercareMessage.id)))
    return thread, msgs


# ---------- 파일 정리 (A가 추가 · B 확인, 결정 23) ----------


def detach_patient_media(db: Session, patient_id: uuid.UUID) -> list[str]:
    """탈퇴: 그 환자가 보낸 사진·영상의 경로를 메시지에서 빼고 돌려줌 (파일은 부르는 쪽이 commit 뒤 Storage에서 지움).
    메시지 글과 "사진 있음"(has_photo)은 병원 쪽 기록이라 남김 (결정 15와 같음). commit은 부르는 쪽."""
    rows = db.scalars(
        select(AftercareMessage)
        .join(AftercareThread, AftercareThread.id == AftercareMessage.thread_id)
        .join(BookingRequest, BookingRequest.id == AftercareThread.request_id)
        .where(BookingRequest.patient_id == patient_id, AftercareMessage.sender == "patient")
    )
    paths: list[str] = []
    for m in rows:
        if m.attachments:
            paths += [a.get("path") for a in m.attachments if a.get("path")]
            m.attachments = []
    return paths


def referenced_media_paths(db: Session) -> set[str]:
    """DB 메시지가 가리키는 파일 전부 (정기 정리에서 이것 밖의 파일만 지움)."""
    out: set[str] = set()
    for atts in db.scalars(select(AftercareMessage.attachments).where(AftercareMessage.has_photo.is_(True))):
        out.update(a.get("path") for a in atts or [] if a.get("path"))
    return out


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
    req = db.get(BookingRequest, thread.request_id)
    to_patient = translate.for_request(db, req.id, text, req.lang, tenant_id) if req else None  # 환자 언어로 (결정 25)
    _add(db, thread, "staff", text, staff_id=sid, translated=to_patient)
    if req:
        notification.notify(db, req.patient_id, "aftercare", req.id)  # 같은 commit (결정 27)
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
