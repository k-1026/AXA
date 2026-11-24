"""방문 전 환자 질문 (A, 결정 32). 예약 요청 뒤 방문 전까지 환자가 병원에 묻는 글 — 병원 답은 기존 상담 답장(replies).

- 환자가 직접 보냄 (챗봇은 초안 카드만, 결정 32). 원문 + 한국어 번역(그 요청서에 번역 동의가 있을 때만, 결정 25)
- 요청서가 지워지면 같이 삭제 (CASCADE). 환자가 탈퇴해도 병원 쪽 상담 기록으로 남음 (요청서와 같음, 결정 15)
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

BigIntId = BigInteger().with_variant(Integer(), "sqlite")


class BookingQuestion(Base):
    __tablename__ = "booking_questions"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"))
    text_original: Mapped[str] = mapped_column(Text)
    text_translated: Mapped[str | None] = mapped_column(Text)  # 병원 직원용 한국어
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (Index("ix_booking_questions_request", "request_id", "created_at"),)
