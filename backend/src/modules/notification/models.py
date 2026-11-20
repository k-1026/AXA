"""사이트 안 알림 (A, 결정 27). 병원이 예약 상태를 바꾸거나 답장하면 환자에게 한 줄.

- 글·건강정보는 넣지 않고 **종류·요청서 id·상태 코드만** → Realtime으로 브라우저에 보내도 안전
- 환자가 탈퇴하면 같이 삭제 (CASCADE), 요청서가 지워져도 삭제
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

KINDS = ("status", "reply", "aftercare")
BigIntId = BigInteger().with_variant(Integer(), "sqlite")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(12))
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"))
    status: Mapped[str | None] = mapped_column(String(12))  # kind=status일 때 바뀐 상태
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    read_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("kind IN ('status', 'reply', 'aftercare')", name="kind"),
        Index("ix_notifications_patient", "patient_id", "created_at"),
    )
