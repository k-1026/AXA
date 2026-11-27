"""방문 전 리마인드 알림 (docs/booking-rules.md 3-2 N1).

확정 예약의 방문 48시간 · 24시간 · 2시간 전에 환자에게 알림(사이트 안 알림 + 웹 푸시)을 보낸다.
- `send_due()`는 정기 작업이 부른다 (POST·GET /api/v1/internal/reminders, 1시간마다 — .github/workflows/reminders.yml)
- 단계 판단은 "지금 남은 시간"으로: 2시간 이하면 2h, 24시간 이하면 24h, 48시간 이하면 48h
  → 작업이 늦게 돌아도 지금 맞는 단계 하나만 보내고, 지나간 앞 단계는 몰아 보내지 않음 (알림 폭탄 방지)
- 보낸 기록 = notifications 행 (kind=reminder, status=단계). 같은 단계·더 늦은 단계를 이미 보냈으면 다시 안 보냄
- 확정이 아닌 예약(취소·변경으로 다시 확인 대기 등)은 보내지 않음. 탈퇴한 환자(patient_id 없음)도 건너뜀
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.booking.models import BookingRequest
from modules.notification.models import Notification
from modules.notification.service import notify

# 늦은 단계부터 (남은 시간이 이 값 이하면 그 단계)
STAGES: tuple[tuple[str, timedelta], ...] = (
    ("2h", timedelta(hours=2)),
    ("24h", timedelta(hours=24)),
    ("48h", timedelta(hours=48)),
)
ORDER = {name: i for i, (name, _) in enumerate(STAGES)}  # 숫자가 작을수록 방문에 가까움


def _utc(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def stage_for(left: timedelta) -> str | None:
    """방문까지 남은 시간 → 보낼 단계. 이미 지났거나 48시간보다 많이 남았으면 None."""
    if left <= timedelta(0):
        return None
    for name, limit in STAGES:
        if left <= limit:
            return name
    return None


def send_due(db: Session, now: datetime | None = None) -> int:
    """지금 보낼 리마인드를 모두 보내고 commit → 보낸 수."""
    now = _utc(now or utcnow())
    rows = db.scalars(
        select(BookingRequest).where(
            BookingRequest.status == "confirmed",
            BookingRequest.patient_id.is_not(None),
            BookingRequest.confirmed_slot.is_not(None),
        )
    )
    sent = 0
    for req in rows:
        stage = stage_for(_utc(req.confirmed_slot) - now)
        if stage is None:
            continue
        done = db.scalars(
            select(Notification.status).where(Notification.request_id == req.id, Notification.kind == "reminder")
        ).all()
        # 같은 단계 또는 더 가까운 단계를 이미 보냈으면 건너뜀 (예: 2h를 보냈는데 24h를 다시 보내지 않음)
        if any(d in ORDER and ORDER[d] <= ORDER[stage] for d in done):
            continue
        notify(db, req.patient_id, "reminder", req.id, stage)
        sent += 1
    db.commit()
    return sent
