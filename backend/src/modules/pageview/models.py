"""병원 상세 페이지 조회 기록 page_events (A, 11/27). 병원 대시보드 "상세페이지 방문자" 숫자의 근거.

- 개인정보 없음: 환자 id·IP·기기 정보를 저장하지 않음. 로그인 여부와 무관
- visitor_key = 브라우저가 만든 무작위 값, **하루마다 바뀜** (docs/dashboard-integration.md page_events)
- 같은 방문자·같은 병원·같은 날(한국 날짜)은 한 줄만 → 줄 수 = 날마다 다른 방문자 수의 합
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Identity, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

BigIntId = BigInteger().with_variant(Integer(), "sqlite")
EVENT_TYPES = ("view",)  # 나중에 click·treatment_view (dashboard-integration.md)


class PageEvent(Base):
    __tablename__ = "page_events"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    hospital_id: Mapped[int] = mapped_column(BigIntId, ForeignKey("hospitals.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(20), default="view")
    visitor_key: Mapped[str] = mapped_column(String(64))
    day: Mapped[date] = mapped_column(Date)  # 한국 날짜
    lang: Mapped[str | None] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint("type IN ('view')", name="type"),
        UniqueConstraint("hospital_id", "type", "visitor_key", "day", name="uq_page_events_once_a_day"),
        Index("ix_page_events_hospital_day", "hospital_id", "day"),
    )
