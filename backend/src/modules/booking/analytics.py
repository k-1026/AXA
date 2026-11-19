"""병원 대시보드 지표 (B). docs/dashboard-integration.md 1-1절·3-1절 `GET /tenant/analytics/summary`.

- 숫자는 `booking_requests`·`booking_events`·`replies`에서 계산. 우리 병원(tenant) 것만
- 값은 코드(`key`·`unit`)만, 화면 글자는 프론트
- 아직 테이블이 없는 지표(방문자 = page_events)는 `None` + `suppressed`에 이름
- "오늘"은 한국 시간 기준
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from modules.booking.models import BookingEvent, BookingRequest, Reply

KST = ZoneInfo("Asia/Seoul")


def _utc_range(start: date, end: date) -> tuple[datetime, datetime]:
    """[start, end] (한국 날짜, 양끝 포함) → UTC [시작, 끝)"""
    a = datetime.combine(start, time.min, KST).astimezone(timezone.utc)
    b = datetime.combine(end + timedelta(days=1), time.min, KST).astimezone(timezone.utc)
    return a, b


def _count_requests(db: Session, tenant_id: uuid.UUID, a: datetime, b: datetime) -> int:
    return db.scalar(
        select(func.count()).select_from(BookingRequest).where(
            BookingRequest.tenant_id == tenant_id, BookingRequest.created_at >= a, BookingRequest.created_at < b
        )
    ) or 0


def _count_events(db: Session, tenant_id: uuid.UUID, to_status: str, a: datetime, b: datetime) -> int:
    return db.scalar(
        select(func.count())
        .select_from(BookingEvent)
        .join(BookingRequest, BookingRequest.id == BookingEvent.request_id)
        .where(
            BookingRequest.tenant_id == tenant_id,
            BookingEvent.to_status == to_status,
            BookingEvent.created_at >= a,
            BookingEvent.created_at < b,
        )
    ) or 0


def _period_numbers(db: Session, tenant_id: uuid.UUID, a: datetime, b: datetime) -> dict:
    confirmed = _count_events(db, tenant_id, "confirmed", a, b)
    cancelled = _count_events(db, tenant_id, "cancelled", a, b)
    return {
        "requests": _count_requests(db, tenant_id, a, b),
        "confirmed": confirmed,
        "visited": _count_events(db, tenant_id, "visited", a, b),
        "cancelRate": round(cancelled / confirmed * 100) if confirmed else None,
    }


def _today(db: Session, tenant_id: uuid.UUID, today: date) -> dict:
    a, b = _utc_range(today, today)
    base = select(func.count()).select_from(BookingRequest).where(BookingRequest.tenant_id == tenant_id)
    sent = exists().where(Reply.request_id == BookingRequest.id, Reply.sent_at.is_not(None))
    return {
        "newRequests": db.scalar(base.where(BookingRequest.status == "pending")) or 0,
        "waitingPatient": db.scalar(base.where(BookingRequest.status == "proposed")) or 0,
        "visitsToday": db.scalar(
            base.where(
                BookingRequest.status == "confirmed",
                BookingRequest.confirmed_slot >= a,
                BookingRequest.confirmed_slot < b,
            )
        )
        or 0,
        "unanswered": db.scalar(base.where(BookingRequest.status == "pending", ~sent)) or 0,
    }


def summary(db: Session, tenant_id: uuid.UUID, start: date, end: date, today: date | None = None) -> dict:
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    now = _period_numbers(db, tenant_id, *_utc_range(start, end))
    prev = _period_numbers(db, tenant_id, *_utc_range(prev_start, prev_end))

    suppressed = ["views"]  # page_events 테이블 전 (대시보드 명세 3단계)
    if now["cancelRate"] is None:
        suppressed.append("cancelRate")
    kpi = [
        {"key": "views", "now": None, "prev": None, "unit": "count"},
        {"key": "requests", "now": now["requests"], "prev": prev["requests"], "unit": "count"},
        {"key": "confirmed", "now": now["confirmed"], "prev": prev["confirmed"], "unit": "count"},
        {"key": "visited", "now": now["visited"], "prev": prev["visited"], "unit": "count"},
        {"key": "cancelRate", "now": now["cancelRate"], "prev": prev["cancelRate"], "unit": "percent", "lowerIsBetter": True},
    ]
    return {
        "period": {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "prevFrom": prev_start.isoformat(),
            "prevTo": prev_end.isoformat(),
        },
        "kpi": kpi,
        "funnel": [
            {"key": "requests", "n": now["requests"]},
            {"key": "confirmed", "n": now["confirmed"]},
            {"key": "visited", "n": now["visited"]},
        ],
        "today": _today(db, tenant_id, today or datetime.now(KST).date()),
        "suppressed": suppressed,
    }
