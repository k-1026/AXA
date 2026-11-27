"""환자용 예약 요청 · 내 예약 API (A). 상태 전이는 booking.service(B)만 함 (contracts 5절).

- `POST /hospitals/{hospital_id}/booking-requests`: 계정 체류 형태 확인(국내 거주 X) → 요청 가능 병원 확인 → 동의 확인 → `create_request` → 동의를 요청서에 묶어 기록
- `GET /me/booking-requests`, `GET /me/booking-requests/{id}`: 내 것만 (남의 것은 404), 답장은 직원이 보낸 것만
- `POST /me/booking-requests/{id}/accept` (병원이 제안한 시간 수락), `/cancel` (pending·proposed에서만)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import PatientPrincipal, current_patient, patient_uuid
from modules.agent import translate
from modules.booking import service
from modules.booking.models import BookingEvent, Reply
from modules.booking.schemas_patient import BookingCreate, CancelIn, PatientBookingOut, QuestionIn, QuestionOut, ReplyOut
from modules.consent import service as consent_service
from modules.hospital import service as hospital_service
from modules.patient import service as patient_service
from modules.question import service as question_service
from modules.tenant.models import Tenant

router = APIRouter(tags=["booking"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


def _required_consents(body: BookingCreate) -> list[str]:
    """privacy(병원에 전달) 항상 · 건강정보가 있으면 health · 글을 번역(해외 LLM)할 때 overseas_transfer."""
    kinds = ["privacy"]
    if body.health_info:
        kinds.append("health")
    if body.message or body.health_info:
        kinds.append("overseas_transfer")
    return kinds


def _out(db: Session, req) -> PatientBookingOut:
    out = PatientBookingOut.model_validate(req)
    replies = db.scalars(
        select(Reply).where(Reply.request_id == req.id, Reply.sent_at.is_not(None)).order_by(Reply.sent_at)
    )
    out.replies = [ReplyOut(text_ko=r.text_ko, text_translated=r.text_translated, sent_at=r.sent_at) for r in replies]
    out.questions = [QuestionOut.model_validate(q, from_attributes=True)
                     for q in question_service.for_requests(db, [req.id])[req.id]]
    if req.status == "rejected":  # 거절 사유 (contracts 2절, booking_events.reason)
        out.reject_reason = db.scalar(
            select(BookingEvent.reason).where(BookingEvent.request_id == req.id, BookingEvent.to_status == "rejected")
            .order_by(BookingEvent.created_at.desc()).limit(1)
        )
    return out


@router.post("/hospitals/{hospital_id}/booking-requests", response_model=PatientBookingOut, status_code=201)
def create(hospital_id: int, body: BookingCreate, db: Db, me: Me):
    patient_id = patient_uuid(me)
    # 계정의 체류 형태 (가입 때 3문항, 결정 28). 본문 residency는 제출 때 한 번 더 확인하는 값
    patient_service.require_short_term(db, patient_id)
    if body.nationality == "KR":  # 한국 국적은 해외에 살아도 받지 않음 (결정 36) — 계정 답과 별개로 요청서 국적도 확인
        raise AppError(403, "residency.not_eligible", "한국 국적은 상담·예약 요청을 할 수 없습니다", {"reason": "korean_nationality"})
    hospital_service.require_requestable(db, hospital_id)  # 미등록·영업 중 아님 → 403, 없으면 404
    tenant = db.scalar(select(Tenant).where(Tenant.hospital_id == hospital_id))
    if tenant is None or not tenant.requests_enabled:
        # 등록 유치기관이지만 메디대구에 입점(병원 계정)하지 않음 → 받을 사람이 없음
        raise AppError(403, "hospital.not_requestable", "상담 요청을 받을 수 없는 병원입니다", {"reason": "not_joined"})

    consent_service.check_versions(body.consents)
    given = {c.kind for c in body.consents}
    missing = [k for k in _required_consents(body) if k not in given]
    if missing:
        raise AppError(422, "consent.required", "필수 동의가 없습니다", {"missing": missing})

    req = service.create_request(
        db,
        patient_id,
        tenant.id,
        dict(
            lang=body.lang,
            nationality=body.nationality,
            contact_method=body.contact_method,
            preferred_slots=[s.isoformat().replace("+00:00", "Z") for s in body.preferred_slots],
            department_code=body.department_code,
            treatment=body.treatment,
            visa_needed=body.visa_needed,
            message_original=body.message,
            health_info=body.health_info,
            patient_timezone=body.patient_timezone,
        ),
    )
    for c in body.consents:  # 이 요청서에 대한 동의로 기록 (consents.booking_request_id)
        consent_service.record(db, patient_id, c.kind, c.version, body.lang, request_id=req.id)
    db.commit()
    if body.message:  # 병원 직원용 한국어 번역 (동의를 기록한 뒤, 실패하면 원문만 — 결정 25)
        ko = translate.for_request(db, req.id, body.message, "ko", tenant.id)
        if ko:
            req.message_translated = ko
            db.commit()
    return _out(db, req)


@router.get("/me/booking-requests", response_model=list[PatientBookingOut])
def my_list(db: Db, me: Me):
    return [_out(db, r) for r in service.list_for_patient(db, patient_uuid(me))]


@router.get("/me/booking-requests/{request_id}", response_model=PatientBookingOut)
def my_detail(request_id: uuid.UUID, db: Db, me: Me):
    return _out(db, service.get_for_patient(db, patient_uuid(me), request_id))


@router.post("/me/booking-requests/{request_id}/accept", response_model=PatientBookingOut)
def accept(request_id: uuid.UUID, db: Db, me: Me):
    return _out(db, service.patient_accept(db, patient_uuid(me), request_id))


@router.post("/me/booking-requests/{request_id}/cancel", response_model=PatientBookingOut)
def cancel(request_id: uuid.UUID, body: CancelIn, db: Db, me: Me):
    return _out(db, service.patient_cancel(db, patient_uuid(me), request_id, body.reason))


@router.post("/me/booking-requests/{request_id}/questions", response_model=PatientBookingOut, status_code=201)
def ask_question(request_id: uuid.UUID, body: QuestionIn, db: Db, me: Me):
    """방문 전 병원에 질문 (결정 32). pending·proposed·confirmed에서만 → 아니면 409. 답은 병원 상담 답장으로."""
    question_service.ask(db, patient_uuid(me), request_id, body.text)
    return _out(db, service.get_for_patient(db, patient_uuid(me), request_id))
