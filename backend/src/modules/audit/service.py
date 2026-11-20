"""열람·처리 기록 남기기 (contracts 5절 `log_action`). 기록만 하고 commit은 하지 않음 → 부르는 쪽 commit에 같이 들어감.

action 목록 (dashboard-integration 5-3, 결정 24)
- `booking.list` 요청서 목록 열람 (ref = "booking_requests:<건수>")
- `booking.view` 요청서 1건 열람 · `booking.reply` 상담 답장 발송 (직원 승인)
- `aftercare.view` 사후관리 대화 열람 (사진 주소 발급 포함) · `aftercare.reply` 사후관리 답장
"""

import threading
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.audit.models import AuditLog

ACTIONS = ("booking.list", "booking.view", "booking.reply", "aftercare.view", "aftercare.reply")
# 목록·열람은 화면이 여러 번 불러도 같은 직원·같은 대상이면 이 시간 안에 1줄만 (대시보드가 한 번 열 때 목록을 7번 부름)
# 답장(*.reply)은 한 번 보낼 때마다 기록
REPEAT_WINDOW = timedelta(minutes=1)
# 화면이 같은 목록을 동시에 여러 번 부르면 DB 확인만으로는 서로 못 봄 → 이 서버 안에서 먼저 막음 (서버가 여러 대면 DB 확인이 뒤를 받침)
_seen: dict[tuple, datetime] = {}
_lock = threading.Lock()


def log_action(db: Session, tenant_id: uuid.UUID, actor: str, action: str, ref: str) -> None:
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action: {action}")
    db.add(AuditLog(tenant_id=tenant_id, actor=str(actor)[:64], action=action, ref=ref[:80]))


def log_and_commit(db: Session, tenant_id: uuid.UUID, actor: str, action: str, ref: str) -> None:
    """조회(GET)처럼 따로 commit이 없는 곳에서. 열람은 1분 안에 같은 기록이 있으면 건너뜀."""
    if not action.endswith(".reply"):
        key = (str(tenant_id), str(actor), action, "list" if action == "booking.list" else ref)
        now = utcnow()
        with _lock:
            last = _seen.get(key)
            if last and now - last < REPEAT_WINDOW:
                return
            _seen[key] = now
            if len(_seen) > 5000:  # 오래된 것 정리
                for k in [k for k, v in _seen.items() if now - v >= REPEAT_WINDOW]:
                    del _seen[k]
        if _recent_same(db, tenant_id, actor, action, ref):
            return
    log_action(db, tenant_id, actor, action, ref)
    db.commit()


def _recent_same(db: Session, tenant_id: uuid.UUID, actor: str, action: str, ref: str) -> bool:
    # 목록은 건수가 바뀌어도 같은 열람으로 봄 (ref = "booking_requests:<건수>")
    same_ref = AuditLog.ref.like("booking_requests:%") if action == "booking.list" else AuditLog.ref == ref[:80]
    return db.scalar(
        select(AuditLog.id).where(
            AuditLog.tenant_id == tenant_id, AuditLog.actor == str(actor)[:64], AuditLog.action == action, same_ref,
            AuditLog.created_at >= utcnow() - REPEAT_WINDOW,
        ).limit(1)
    ) is not None


def recent(db: Session, tenant_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
    return list(db.scalars(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.id.desc()).limit(limit)
    ))
