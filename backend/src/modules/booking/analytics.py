"""병원 대시보드 지표 (B). docs/dashboard-integration.md 1-1절·3-1절 `GET /tenant/analytics/summary`.

- 숫자는 `booking_requests`·`booking_events`·`replies`에서 계산. 우리 병원(tenant) 것만
- 값은 코드(`key`·`unit`)만, 화면 글자는 프론트
- 아직 테이블이 없는 지표(방문자 = page_events)는 `None` + `suppressed`에 이름
- "오늘"은 한국 시간 기준
- `series`: 그래프용 구간별 숫자를 한 번에 (11/27, 대시보드가 구간마다 summary를 따로 부르던 것 → 1번). 조회 2번 후 한국 날짜로 나눔
"""

import uuid
from collections import Counter
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


SERIES_MAX_BUCKETS = 12  # 그래프 점 수 (프론트 KpiTrends와 같게)
SERIES_MAX_DAYS = 366


def _kst_day(ts: datetime) -> date:
    if ts.tzinfo is None:  # SQLite(테스트)는 시간대 없이 돌려줌 → UTC로 저장된 값
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(KST).date()


def series(db: Session, tenant_id: uuid.UUID, start: date, end: date) -> dict:
    """[start, end]를 최대 12구간으로 나눠 구간마다 요청·확정·방문·취소율. 지난 기간(같은 길이 바로 앞)도 같은 위치로 나눔.

    구간 숫자는 그 구간으로 summary를 부른 kpi의 now와 같음."""
    days = (end - start).days + 1
    size = -(-days // SERIES_MAX_BUCKETS)
    prev_start = start - timedelta(days=days)
    a, _ = _utc_range(prev_start, prev_start)
    _, b = _utc_range(end, end)

    per_day: Counter[tuple[str, date]] = Counter()
    created = db.scalars(
        select(BookingRequest.created_at).where(
            BookingRequest.tenant_id == tenant_id, BookingRequest.created_at >= a, BookingRequest.created_at < b
        )
    )
    for ts in created:
        per_day["requests", _kst_day(ts)] += 1
    events = db.execute(
        select(BookingEvent.to_status, BookingEvent.created_at)
        .join(BookingRequest, BookingRequest.id == BookingEvent.request_id)
        .where(
            BookingRequest.tenant_id == tenant_id,
            BookingEvent.to_status.in_(("confirmed", "cancelled", "visited")),
            BookingEvent.created_at >= a,
            BookingEvent.created_at < b,
        )
    )
    for to_status, ts in events:
        per_day[to_status, _kst_day(ts)] += 1

    def numbers(d0: date, d1: date) -> dict:
        span = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
        n = {k: sum(per_day[k, d] for d in span) for k in ("requests", "confirmed", "visited", "cancelled")}
        return {
            "requests": n["requests"],
            "confirmed": n["confirmed"],
            "visited": n["visited"],
            "cancelRate": round(n["cancelled"] / n["confirmed"] * 100) if n["confirmed"] else None,
        }

    buckets = []
    for i in range(0, days, size):
        j = min(i + size, days) - 1
        buckets.append({
            "from": (start + timedelta(days=i)).isoformat(),
            "to": (start + timedelta(days=j)).isoformat(),
            "now": numbers(start + timedelta(days=i), start + timedelta(days=j)),
            "prev": numbers(prev_start + timedelta(days=i), prev_start + timedelta(days=j)),
        })
    return {"size": size, "buckets": buckets}
