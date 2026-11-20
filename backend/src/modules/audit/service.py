"""열람·처리 기록 남기기 (contracts 5절 `log_action`). 기록만 하고 commit은 하지 않음 → 부르는 쪽 commit에 같이 들어감.

action 목록 (dashboard-integration 5-3, 결정 24)
- `booking.list` 요청서 목록 열람 (ref = "booking_requests:<건수>")
- `booking.view` 요청서 1건 열람 · `booking.reply` 상담 답장 발송 (직원 승인)
- `aftercare.view` 사후관리 대화 열람 (사진 주소 발급 포함) · `aftercare.reply` 사후관리 답장
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.audit.models import AuditLog

ACTIONS = ("booking.list", "booking.view", "booking.reply", "aftercare.view", "aftercare.reply")


def log_action(db: Session, tenant_id: uuid.UUID, actor: str, action: str, ref: str) -> None:
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action: {action}")
    db.add(AuditLog(tenant_id=tenant_id, actor=str(actor)[:64], action=action, ref=ref[:80]))


def log_and_commit(db: Session, tenant_id: uuid.UUID, actor: str, action: str, ref: str) -> None:
    """조회(GET)처럼 따로 commit이 없는 곳에서."""
    log_action(db, tenant_id, actor, action, ref)
    db.commit()


def recent(db: Session, tenant_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
    return list(db.scalars(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.id.desc()).limit(limit)
    ))
