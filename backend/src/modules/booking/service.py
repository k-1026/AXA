"""예약 상태 흐름 (B 주인). 상태 전이 규칙은 **이 파일 한 곳**에만 둔다.

- 환자 쪽 함수(`create_request`, `list_for_patient`, `get_for_patient`, `patient_accept`, `patient_cancel`)는
  A의 `router_patient.py`가 부른다 (docs/backend-contracts.md 5절)
- 병원 쪽 함수(`staff_*`)는 `router_tenant.py`(B)가 부른다. tenant_id로만 조회 → 남의 병원 요청은 404
- 모든 상태 변경은 `booking_events`에 1건씩 남긴다 (지우지 않음)
- TODO(A 함수 생기면): 상태 변경마다 `notification.service.notify()` 호출, 생성 시 `consent.service.require()`
"""

import uuid
from datetime import datetime, timedelta, timezone
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


# ---------- 중복 예약 규칙 (docs/booking-rules.md) ----------
# 한 환자의 "살아 있는" 예약(확인 대기·시간 제안·확정)끼리 시간이 겹치지 않게 한다.
# - 시간 간격: 어느 병원이든 다른 예약 시간 앞뒤 60분 안에는 새 요청 불가 (이동·진료 시간)
# - 같은 병원 같은 날: 하루 1건 (시간을 바꾸려면 기존 요청을 변경·취소)
# - 처리 전 요청(확인 대기·시간 제안)은 한 사람당 최대 5건 (여기저기 걸어 두고 노쇼하는 것 방지)
# 확인 대기 요청은 희망 시간 1~3개를 모두 "잡힌 시간"으로 본다 (병원이 그중 하나로 확정할 수 있음)
BUFFER = timedelta(minutes=60)
MAX_OPEN = 5
ACTIVE = ("pending", "proposed", "confirmed")
KST = ZoneInfo("Asia/Seoul")


def _utc(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def _held_slots(r: BookingRequest) -> list[datetime]:
    """그 예약이 잡고 있는 시간 (UTC). 시간 제안·확정이면 그 시간, 확인 대기면 희망 시간 전부."""
    if r.status in ("proposed", "confirmed") and r.confirmed_slot is not None:
        return [_utc(r.confirmed_slot)]
    out = []
    for s in r.preferred_slots or []:
        try:
            out.append(_utc(datetime.fromisoformat(str(s).replace("Z", "+00:00"))))
        except ValueError:
            continue
    return out


def _check_patient_slots(
    db: Session,
    patient_id: uuid.UUID,
    tenant_id: uuid.UUID,
    slots: list[datetime],
    *,
    exclude: uuid.UUID | None = None,
    statuses: tuple[str, ...] = ACTIVE,
) -> None:
    """slots가 같은 환자의 다른 살아 있는 예약과 겹치면 409. exclude = 지금 바꾸는 그 요청."""
    q = select(BookingRequest).where(BookingRequest.patient_id == patient_id, BookingRequest.status.in_(statuses))
    if exclude is not None:
        q = q.where(BookingRequest.id != exclude)
    new = [_utc(s) for s in slots]
    for o in db.scalars(q):
        held = _held_slots(o)
        if o.tenant_id == tenant_id:
            days = {h.astimezone(KST).date() for h in held}
            hit = next((s for s in new if s.astimezone(KST).date() in days), None)
            if hit is not None:
                raise AppError(409, "booking.same_day", "같은 병원에 그날 예약(요청)이 이미 있습니다",
                               {"request_id": str(o.id), "date": hit.astimezone(KST).date().isoformat()})
        for s in new:
            near = next((h for h in held if abs(h - s) < BUFFER), None)
            if near is not None:
                raise AppError(409, "booking.time_conflict", "다른 예약 시간과 1시간 이내로 겹칩니다",
                               {"request_id": str(o.id), "hospital_id": o.hospital_id,
                                "slot": near.isoformat().replace("+00:00", "Z"), "buffer_minutes": 60})


def create_request(db: Session, patient_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> BookingRequest:
    """요청서 생성. 상태는 항상 pending. 등록 유치의료기관(requests_enabled)만 받음.
    같은 병원에 처리 전 요청이 있어도 날짜가 다르면 받는다 (11/26 결정 — 예전 booking.duplicate 대신 시간 규칙)."""
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or not tenant.requests_enabled:
        raise _not_found()
    open_count = len(list(db.scalars(select(BookingRequest.id).where(
        BookingRequest.patient_id == patient_id, BookingRequest.status.in_(("pending", "proposed"))))))
    if open_count >= MAX_OPEN:
        raise AppError(409, "booking.too_many", f"처리 전 요청은 {MAX_OPEN}건까지 보낼 수 있습니다", {"max": MAX_OPEN})
    slots = [datetime.fromisoformat(str(s).replace("Z", "+00:00")) for s in data.get("preferred_slots") or []]
    _check_patient_slots(db, patient_id, tenant_id, slots)
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
    req = get_for_patient(db, patient_id, request_id)
    if req.status == "proposed" and req.confirmed_slot is not None:
        # 병원이 제안한 시간이 이미 확정된 다른 예약과 겹치면 수락 불가 (확인 대기 요청끼리는 막지 않음)
        _check_patient_slots(db, patient_id, req.tenant_id, [req.confirmed_slot], exclude=req.id, statuses=("confirmed",))
    return _move(db, req, "patient_accept", "patient", str(patient_id))


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
    if action in ("confirm", "propose") and req.patient_id is not None:
        # 병원이 정하려는 시간이 그 환자의 다른 확정 예약과 1시간 이내면 다른 시간을 고르게 함
        when = slot or req.confirmed_slot or next(iter(_held_slots(req)), None)
        if when is not None:
            try:
                _check_patient_slots(db, req.patient_id, req.tenant_id, [when], exclude=req.id, statuses=("confirmed",))
            except AppError as e:
                raise AppError(409, "booking.patient_conflict",
                               "환자의 다른 확정 예약과 시간이 겹칩니다. 다른 시간을 제안하세요", e.detail) from e
    return _move(db, req, action, "staff", staff_id, slot=slot, reason=reason)


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
