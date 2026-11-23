"""알림 쓰기·읽기 (A, contracts 5절 `notify`, 결정 27).

- `notify()`는 commit하지 않음 → 상태 변경·답장과 **같은 처리 안에서** 저장 (둘 중 하나만 남지 않게)
- 환자에게 알릴 상태: confirmed·rejected·proposed·visited·no_show·expired (환자가 직접 한 취소·수락은 X)
- Realtime 토큰: Supabase가 믿는 HS256 토큰(sub = 환자 id, role = authenticated, 1시간). RLS가 자기 알림만 보여 줌
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import utcnow
from core.errors import AppError
from modules.booking.models import BookingRequest
from modules.notification import push
from modules.notification.models import KINDS, Notification

NOTIFY_STATUS = ("confirmed", "rejected", "proposed", "visited", "no_show", "expired")
LIST_LIMIT = 50
REALTIME_TTL = timedelta(hours=1)


def notify(db: Session, patient_id: uuid.UUID | None, kind: str, request_id: uuid.UUID, status: str | None = None) -> None:
    if patient_id is None:  # 탈퇴한 환자의 요청서
        return
    if kind not in KINDS or (kind == "status" and status not in NOTIFY_STATUS):
        return
    db.add(Notification(patient_id=patient_id, kind=kind, request_id=request_id, status=status))
    push.queue(db, patient_id, kind, request_id, status)  # 구독한 브라우저에 commit 뒤 푸시 (결정 30)


def list_mine(db: Session, patient_id: uuid.UUID) -> list[tuple[Notification, int | None]]:
    """최근 순 (알림, 병원 id). 읽은 것도 포함 (화면이 안 읽은 것만 셈)."""
    rows = db.execute(
        select(Notification, BookingRequest.hospital_id)
        .join(BookingRequest, BookingRequest.id == Notification.request_id, isouter=True)
        .where(Notification.patient_id == patient_id)
        .order_by(Notification.id.desc())
        .limit(LIST_LIMIT)
    ).all()
    return [(n, h) for n, h in rows]


def mark_read(db: Session, patient_id: uuid.UUID, ids: list[int] | None) -> int:
    """ids가 없으면 모두. 남의 알림 id는 무시 → 바뀐 수."""
    q = update(Notification).where(Notification.patient_id == patient_id, Notification.read_at.is_(None))
    if ids is not None:
        q = q.where(Notification.id.in_(ids))
    n = db.execute(q.values(read_at=utcnow())).rowcount or 0
    db.commit()
    return n


def realtime_token(patient_id: uuid.UUID) -> tuple[str, datetime]:
    s = get_settings()
    if not (s.supabase_jwt_secret and s.supabase_url):
        raise AppError(503, "realtime.unavailable", "실시간 알림을 쓸 수 없습니다")
    now = datetime.now(timezone.utc)
    exp = now + REALTIME_TTL
    token = jwt.encode(
        {"sub": str(patient_id), "role": "authenticated", "aud": "authenticated", "iat": now, "exp": exp},
        s.supabase_jwt_secret,
        algorithm="HS256",
    )
    return token, exp
