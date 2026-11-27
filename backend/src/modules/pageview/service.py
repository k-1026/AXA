"""상세 페이지 조회 기록·집계 (A)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.hospital.models import Hospital
from modules.pageview.models import PageEvent

KST = ZoneInfo("Asia/Seoul")


def record_view(db: Session, ykiho: str, visitor_key: str, lang: str | None, today: date | None = None) -> bool:
    """→ 새로 셌으면 True, 오늘 이미 센 방문자면 False. 없는 병원은 404."""
    hospital_id = db.scalar(select(Hospital.id).where(Hospital.ykiho == ykiho))
    if hospital_id is None:
        raise AppError(404, "not_found", "병원을 찾을 수 없습니다")
    day = today or datetime.now(KST).date()
    seen = db.scalar(
        select(PageEvent.id).where(
            PageEvent.hospital_id == hospital_id, PageEvent.type == "view",
            PageEvent.visitor_key == visitor_key, PageEvent.day == day,
        )
    )
    if seen is not None:
        return False
    db.add(PageEvent(hospital_id=hospital_id, type="view", visitor_key=visitor_key, day=day, lang=lang))
    try:
        db.commit()
    except IntegrityError:  # 같은 순간 두 번 (새로고침 연타) → 하나만
        db.rollback()
        return False
    return True


def count_views(db: Session, hospital_id: int, start: date, end: date) -> int:
    """[start, end] 한국 날짜, 양끝 포함. 날마다 다른 방문자 수의 합"""
    return db.scalar(
        select(func.count()).select_from(PageEvent).where(
            PageEvent.hospital_id == hospital_id, PageEvent.type == "view", PageEvent.day >= start, PageEvent.day <= end
        )
    ) or 0


def views_per_day(db: Session, hospital_id: int, start: date, end: date) -> dict[date, int]:
    rows = db.execute(
        select(PageEvent.day, func.count())
        .where(PageEvent.hospital_id == hospital_id, PageEvent.type == "view", PageEvent.day >= start, PageEvent.day <= end)
        .group_by(PageEvent.day)
    )
    return {d: n for d, n in rows}
