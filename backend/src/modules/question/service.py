"""방문 전 환자 질문 (A, 결정 32). 상태 확인은 booking.service(B)의 `get_for_patient`로만."""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.agent import translate
from modules.booking import service as booking_service
from modules.notification import service as notification
from modules.question.models import BookingQuestion

OPEN_STATUS = ("pending", "proposed", "confirmed")  # 방문 전 (방문 뒤는 사후관리, 결정 26)
MAX_PER_REQUEST = 30


def ask(db: Session, patient_id: uuid.UUID, request_id: uuid.UUID, text: str) -> BookingQuestion:
    req = booking_service.get_for_patient(db, patient_id, request_id)  # 남의 것·없음 → 404
    if req.status not in OPEN_STATUS:
        raise AppError(409, "booking.invalid_transition", "방문 전 예약에만 질문을 보낼 수 있습니다",
                       {"status": req.status, "allowed": list(OPEN_STATUS)})
    n = db.scalar(select(func.count()).select_from(BookingQuestion).where(BookingQuestion.request_id == request_id))
    if n >= MAX_PER_REQUEST:
        raise AppError(429, "rate_limited", "이 예약에 보낼 수 있는 질문 수를 넘었습니다", {"limit": "request"})
    q = BookingQuestion(request_id=request_id, text_original=text)
    db.add(q)
    notification.notify_staff(db, req.tenant_id, "question", req.id)  # 병원 대시보드에 바로 (11/27)
    db.commit()
    ko = translate.for_request(db, request_id, text, "ko", req.tenant_id)  # 동의가 있을 때만, 실패하면 원문만
    if ko:
        q.text_translated = ko
        db.commit()
    return q


def for_requests(db: Session, request_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[BookingQuestion]]:
    """요청서 id → 질문 (보낸 순). 한 번에 조회."""
    out: dict[uuid.UUID, list[BookingQuestion]] = defaultdict(list)
    if request_ids:
        for q in db.scalars(select(BookingQuestion).where(BookingQuestion.request_id.in_(request_ids))
                            .order_by(BookingQuestion.created_at, BookingQuestion.id)):
            out[q.request_id].append(q)
    return out
