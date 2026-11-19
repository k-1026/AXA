"""상담·예약 요청 (B). docs/backend-plan.md 4-2절, docs/backend-contracts.md 2절, docs/dashboard-integration.md 2절.

- `booking_requests`: 환자가 병원 1곳에 보낸 요청서. 상태 기본값 `pending`
- `booking_events`: 상태 이력. **지우지 않음** (대시보드 지표는 여기서 계산)
- `replies`: 병원 답장. 직원 승인(`sent_at`) 전에는 환자에게 안 보임
- 상태에 `visited`·`no_show` 추가 (대시보드 명세 2-3, B 결정 2026-11-17)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow
from modules.patient.models import LANGS

STATUSES = ("pending", "proposed", "confirmed", "rejected", "cancelled", "expired", "visited", "no_show")
ACTORS = ("patient", "staff", "system")
CANCEL_REASONS = ("schedule", "cost", "interpreter", "transport", "other_hospital", "other", "none")
REPLY_KINDS = ("template", "free")

JsonType = JSON().with_variant(JSONB(), "postgresql")
# bigint identity (SQLite 테스트에서는 INTEGER PRIMARY KEY로 자동 증가)
BigIntId = BigInteger().with_variant(Integer(), "sqlite")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{x}'" for x in values) + ")"


class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # 탈퇴하면 계정 행을 바로 지움(결정 15) → 병원 쪽 기록은 남기고 연결만 끊음
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospitals.id"))  # FK는 A 리비전 0007
    status: Mapped[str] = mapped_column(String(12), default="pending")
    lang: Mapped[str] = mapped_column(String(8))
    nationality: Mapped[str] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    contact_method: Mapped[str] = mapped_column(String(20))
    preferred_slots: Mapped[list] = mapped_column(JsonType, default=list)  # UTC ISO 문자열 1~3개
    department_code: Mapped[str] = mapped_column(String(30))
    treatment: Mapped[str | None] = mapped_column(String(60))  # 진료항목 코드 (대시보드 1-2)
    visa_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    message_original: Mapped[str | None] = mapped_column(Text)
    message_translated: Mapped[str | None] = mapped_column(Text)
    health_info: Mapped[str | None] = mapped_column(Text)  # 선택. 있으면 health 동의 필수
    patient_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")
    channel: Mapped[str] = mapped_column(String(20), default="direct")  # 홍보 링크 코드
    confirmed_slot: Mapped[datetime | None]  # 확정·제안된 시간 (UTC)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(_in("status", STATUSES), name="status"),
        CheckConstraint(_in("lang", LANGS), name="lang"),
        Index("ix_booking_requests_tenant_created", "tenant_id", "created_at"),
        Index("ix_booking_requests_tenant_status", "tenant_id", "status"),
        Index("ix_booking_requests_patient", "patient_id", "created_at"),
    )


class BookingEvent(Base):
    __tablename__ = "booking_events"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"))
    from_status: Mapped[str | None] = mapped_column(String(12))  # 생성 이벤트는 None
    to_status: Mapped[str] = mapped_column(String(12))
    actor_type: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[str | None] = mapped_column(String(64))
    proposed_slot: Mapped[datetime | None]
    reason: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint(_in("to_status", STATUSES), name="to_status"),
        CheckConstraint(_in("actor_type", ACTORS), name="actor_type"),
        Index("ix_booking_events_request", "request_id", "created_at"),
        Index("ix_booking_events_to_status_created", "to_status", "created_at"),
    )


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(10), default="free")
    text_ko: Mapped[str] = mapped_column(Text)
    text_translated: Mapped[str | None] = mapped_column(Text)
    ai_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id", ondelete="SET NULL"))
    sent_at: Mapped[datetime | None]  # None이면 초안 (환자에게 안 보임)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint(_in("kind", REPLY_KINDS), name="kind"),
        Index("ix_replies_request", "request_id", "created_at"),
    )
