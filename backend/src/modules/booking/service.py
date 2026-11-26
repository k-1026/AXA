"""예약 상태 흐름 (B 주인). 상태 전이 규칙은 **이 파일 한 곳**에만 둔다.

- 환자 쪽 함수(`create_request`, `list_for_patient`, `get_for_patient`, `patient_accept`, `patient_cancel`)는
  A의 `router_patient.py`가 부른다 (docs/backend-contracts.md 5절)
- 병원 쪽 함수(`staff_*`)는 `router_tenant.py`(B)가 부른다. tenant_id로만 조회 → 남의 병원 요청은 404
- 모든 상태 변경은 `booking_events`에 1건씩 남긴다 (지우지 않음)
- TODO(A 함수 생기면): 상태 변경마다 `notification.service.notify()` 호출, 생성 시 `consent.service.require()`
"""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from modules.agent import translate
from modules.notification import service as notification
from modules.booking.models import CANCEL_REASONS, REJECT_REASONS, BookingEvent, BookingRequest, Reply
from modules.hospital.models import HospitalHours
from modules.tenant.models import StaffUser, Tenant

# (현재 상태, 행동) → 다음 상태. 여기 없는 조합은 409 booking.invalid_transition
TRANSITIONS: dict[tuple[str, str], str] = {
    ("pending", "confirm"): "confirmed",
    # ("proposed", "confirm") 없음: 병원이 제안한 시간은 환자가 수락해야 확정 (patient_accept). 병원은 다시 제안·거절만 (11/24 사용자 결정, A 수정)
    ("pending", "reject"): "rejected",
    ("proposed", "reject"): "rejected",
    ("pending", "propose"): "proposed",
    ("proposed", "propose"): "proposed",  # 다른 시간으로 다시 제안
    ("confirmed", "visited"): "visited",
    ("confirmed", "no_show"): "no_show",
    # 환자
    ("proposed", "patient_accept"): "confirmed",
    ("pending", "patient_cancel"): "cancelled",
    ("proposed", "patient_cancel"): "cancelled",  # 제안 거절 = 취소 (B 결정 2026-11-17)
}
STAFF_ACTIONS = ("confirm", "reject", "propose", "visited", "no_show")


def _not_found() -> AppError:
    return AppError(404, "not_found", "요청을 찾을 수 없습니다")


def _move(
    db: Session,
    req: BookingRequest,
    action: str,
    actor_type: str,
    actor_id: str | None,
    *,
    slot: datetime | None = None,
    reason: str | None = None,
) -> BookingRequest:
    nxt = TRANSITIONS.get((req.status, action))
    if nxt is None:
        raise AppError(
            409,
            "booking.invalid_transition",
            "지금 상태에서는 할 수 없는 변경입니다",
            {"from": req.status, "action": action},
        )
    if action in ("confirm", "propose") and slot is None and req.confirmed_slot is None:
        raise AppError(422, "validation", "시간을 입력하세요", {"errors": [{"loc": ["slot"], "type": "missing"}]})
    db.add(
        BookingEvent(
            request_id=req.id,
            from_status=req.status,
            to_status=nxt,
            actor_type=actor_type,
            actor_id=actor_id,
            proposed_slot=slot,
            reason=reason,
        )
    )
    if slot is not None:
        req.confirmed_slot = slot
    req.status = nxt
    req.updated_at = utcnow()
    if actor_type != "patient":  # 병원·시스템이 바꾼 것만 환자에게 알림 (같은 commit, 결정 27)
        notification.notify(db, req.patient_id, "status", req.id, nxt)
    db.commit()
    db.refresh(req)
    return req


# ---------- 환자 쪽 (A가 호출) ----------


def create_request(db: Session, patient_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> BookingRequest:
    """요청서 생성. 상태는 항상 pending. 등록 유치의료기관(requests_enabled)만 받음."""
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or not tenant.requests_enabled:
        raise _not_found()
    dup = db.scalar(
        select(BookingRequest.id).where(
            BookingRequest.patient_id == patient_id,
            BookingRequest.tenant_id == tenant_id,
            BookingRequest.status.in_(("pending", "proposed")),
        )
    )
    if dup is not None:
        raise AppError(409, "booking.duplicate", "이 병원에 처리 안 된 요청이 이미 있습니다")
    req = BookingRequest(patient_id=patient_id, tenant_id=tenant_id, hospital_id=tenant.hospital_id, **data)
    db.add(req)
    db.flush()
    db.add(BookingEvent(request_id=req.id, from_status=None, to_status="pending", actor_type="patient", actor_id=str(patient_id)))
    db.commit()
    db.refresh(req)
    return req


def list_for_patient(db: Session, patient_id: uuid.UUID) -> list[BookingRequest]:
    return list(
        db.scalars(
            select(BookingRequest)
            .where(BookingRequest.patient_id == patient_id)
            .order_by(BookingRequest.created_at.desc())
        )
    )


def get_for_patient(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID) -> BookingRequest:
    req = db.get(BookingRequest, request_id)
    if req is None or req.patient_id != patient_id:
        raise _not_found()  # 남의 요청도 404
    return req


def patient_accept(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID) -> BookingRequest:
    return _move(db, get_for_patient(db, patient_id, request_id), "patient_accept", "patient", str(patient_id))


def patient_cancel(
    db: Session, patient_id: uuid.UUID, request_id: uuid.UUID, reason: str | None = None
) -> BookingRequest:
    if reason is not None and reason not in CANCEL_REASONS:
        raise AppError(422, "validation", "취소 사유 코드가 올바르지 않습니다", {"errors": [{"loc": ["reason"], "type": "enum"}]})
    req = get_for_patient(db, patient_id, request_id)
    return _move(db, req, "patient_cancel", "patient", str(patient_id), reason=reason)


# ---------- 병원 쪽 (B router_tenant) ----------


def staff_get(db: Session, tenant_id: uuid.UUID, request_id: uuid.UUID) -> BookingRequest:
    req = db.get(BookingRequest, request_id)
    if req is None or req.tenant_id != tenant_id:
        raise _not_found()  # 다른 병원 요청은 404
    return req


def staff_list(
    db: Session,
    tenant_id: uuid.UUID,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[BookingRequest]:
    q = select(BookingRequest).where(BookingRequest.tenant_id == tenant_id)
    if status:
        q = q.where(BookingRequest.status == status)
    if start:
        q = q.where(BookingRequest.created_at >= start)
    if end:
        q = q.where(BookingRequest.created_at < end)
    return list(db.scalars(q.order_by(BookingRequest.created_at.desc())))


def staff_act(
    db: Session,
    tenant_id: uuid.UUID,
    staff_id: str,
    request_id: uuid.UUID,
    action: str,
    slot: datetime | None = None,
    reason: str | None = None,
) -> BookingRequest:
    if action not in STAFF_ACTIONS:
        raise AppError(409, "booking.invalid_transition", "지금 상태에서는 할 수 없는 변경입니다", {"action": action})
    if reason is not None and (action != "reject" or reason not in REJECT_REASONS):  # 거절 사유는 거절에만, 정해진 코드만
        raise AppError(422, "validation", "거절 사유 코드가 올바르지 않습니다", {"errors": [{"loc": ["reason"], "type": "enum"}]})
    req = staff_get(db, tenant_id, request_id)
    if action == "propose" and slot is not None:
        _check_open(db, req.hospital_id, slot)
    return _move(db, req, action, "staff", staff_id, slot=slot, reason=reason)


KST = ZoneInfo("Asia/Seoul")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _check_open(db: Session, hospital_id: int, slot: datetime) -> None:
    """제안 시간이 그 병원 진료시간 안인지 (한국 시간). 휴진일·진료 전후·점심이면 422 validation.
    그날 진료시간 데이터가 없거나 unknown이면 막지 않음 (모르는 것을 휴진으로 보지 않음)."""
    local = slot.astimezone(KST)
    h = db.get(HospitalHours, (hospital_id, DAYS[local.weekday()]))
    if h is None or h.state not in ("open", "closed"):
        return
    t = local.time()
    closed = (h.state == "closed" or h.open_time is None or h.close_time is None
              or not (h.open_time <= t < h.close_time)
              or (h.lunch_start is not None and h.lunch_end is not None and h.lunch_start <= t < h.lunch_end))
    if closed:
        raise AppError(422, "validation", "병원 진료시간이 아닙니다 (휴진일·진료 전후·점심)",
                       {"errors": [{"loc": ["slot"], "type": "closed"}]})


# ---------- 상담 답장 (병원 직원) ----------
# 대시보드의 "보내기" 확인 창 = 직원 승인 → 바로 보낸 상태(sent_at)로 저장. AI 초안은 승인 전 저장하지 않음 (compliance: 승인 없이 발송 X)
# 번역(text_translated)은 ai/llm 연결 전이라 비움 → 환자 화면은 원문(한국어)


def staff_reply(db: Session, tenant_id: uuid.UUID, staff_id: str, request_id: uuid.UUID, text: str) -> Reply:
    req = staff_get(db, tenant_id, request_id)  # 다른 병원 요청은 404
    if not text.strip():
        raise AppError(422, "validation", "내용을 입력하세요", {"errors": [{"loc": ["text"], "type": "missing"}]})
    try:
        approver = db.get(StaffUser, uuid.UUID(staff_id))
    except ValueError:
        approver = None
    reply = Reply(
        request_id=req.id,
        kind="free",
        text_ko=text.strip(),
        text_translated=translate.for_request(db, req.id, text, req.lang, tenant_id),  # 환자 언어로, 동의 없거나 실패면 None (결정 25)
        ai_draft=False,
        approved_by=approver.id if approver and approver.tenant_id == tenant_id else None,
        sent_at=utcnow(),
    )
    db.add(reply)
    notification.notify(db, req.patient_id, "reply", req.id)
    db.commit()
    db.refresh(reply)
    return reply


def sent_replies(db: Session, request_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Reply]]:
    """요청 id → 보낸 답장(보낸 순). 병원 목록·상세 응답에 붙임 (tenant 확인이 끝난 요청 id만 넘길 것)."""
    out: dict[uuid.UUID, list[Reply]] = {i: [] for i in request_ids}
    if not request_ids:
        return out
    rows = db.scalars(
        select(Reply).where(Reply.request_id.in_(request_ids), Reply.sent_at.is_not(None)).order_by(Reply.sent_at)
    )
    for r in rows:
        out[r.request_id].append(r)
    return out
