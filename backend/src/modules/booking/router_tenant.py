"""병원용 예약·대시보드 API (B). 모든 경로는 직원 토큰의 tenant_id로만 조회."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import StaffPrincipal, current_staff
from modules.booking import analytics, service
from modules.booking.schemas import BookingOut, ReplyIn, ReplyOut, StaffAction, TenantBookingOut

router = APIRouter(prefix="/tenant", tags=["tenant"])

Db = Annotated[Session, Depends(get_db)]
Staff = Annotated[StaffPrincipal, Depends(current_staff)]


def _tenant(staff: StaffPrincipal) -> uuid.UUID:
    try:
        return uuid.UUID(staff.tenant_id)
    except ValueError:
        raise AppError(401, "auth.required", "로그인이 필요합니다")


def _with_replies(db: Session, reqs: list) -> list[TenantBookingOut]:
    """요청서 + 보낸 답장 (한 번에 조회)"""
    replies = service.sent_replies(db, [r.id for r in reqs])
    return [
        TenantBookingOut.model_validate(r).model_copy(update={"replies": [ReplyOut.model_validate(x) for x in replies[r.id]]})
        for r in reqs
    ]


@router.get("/booking-requests", response_model=list[TenantBookingOut])
def list_requests(
    db: Db,
    staff: Staff,
    status: str | None = None,
    start: Annotated[datetime | None, Query(alias="from")] = None,
    end: Annotated[datetime | None, Query(alias="to")] = None,
):
    return _with_replies(db, service.staff_list(db, _tenant(staff), status, start, end))


@router.get("/booking-requests/{request_id}", response_model=TenantBookingOut)
def get_request(request_id: uuid.UUID, db: Db, staff: Staff):
    return _with_replies(db, [service.staff_get(db, _tenant(staff), request_id)])[0]


# /{action}보다 먼저 등록해야 "replies"가 행동 이름으로 잡히지 않음
@router.post("/booking-requests/{request_id}/replies", response_model=ReplyOut, status_code=201)
def reply(request_id: uuid.UUID, body: ReplyIn, db: Db, staff: Staff):
    """상담 답장 저장·발송 (직원이 확인 창에서 보내기 = 승인). 환자는 GET /me/booking-requests의 replies로 봄"""
    return service.staff_reply(db, _tenant(staff), staff.staff_id, request_id, body.text)


@router.post("/booking-requests/{request_id}/{action}", response_model=BookingOut)
def act(
    request_id: uuid.UUID,
    action: Literal["confirm", "reject", "propose", "visited", "no-show"],
    db: Db,
    staff: Staff,
    body: StaffAction | None = None,
):
    return service.staff_act(
        db, _tenant(staff), staff.staff_id, request_id, action.replace("-", "_"),
        body.slot if body else None, reason=body.reason if body else None,
    )


@router.get("/analytics/summary")
def analytics_summary(
    db: Db,
    staff: Staff,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
):
    """기본 기간 = 이번 달 1일 ~ 오늘 (한국 날짜)."""
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    end = end or today
    start = start or end.replace(day=1)
    if start > end:
        raise AppError(422, "validation", "기간이 올바르지 않습니다", {"errors": [{"loc": ["from"], "type": "range"}]})
    return analytics.summary(db, _tenant(staff), start, end, today)
