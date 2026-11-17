"""사후관리 대화 (B). docs/dashboard-integration.md 1-4절·6절.

- 방문 완료(`visited`)된 요청서 1건에 대화 1개 (`request_id` 유일)
- 병원 계정(tenant)에 묶임 → 병원 직원은 자기 병원 대화만 봄
- 메시지 본문은 건강정보가 들어갈 수 있음 → 해당 병원 직원만 열람 (열람 기록 audit_logs는 다음 단계)
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, ForeignKey, Identity, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

THREAD_STATUSES = ("new", "in_progress", "resolved")
SENDERS = ("patient", "staff")

JsonType = JSON().with_variant(JSONB(), "postgresql")
BigIntId = BigInteger().with_variant(Integer(), "sqlite")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{x}'" for x in values) + ")"


class AftercareThread(Base):
    __tablename__ = "aftercare_threads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(12), default="new")
    tags: Mapped[list] = mapped_column(JsonType, default=list)  # 처음엔 직원이 고름, AI 요약은 agent 단계 뒤
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_message_at: Mapped[datetime] = mapped_column(default=utcnow)
    resolved_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint(_in("status", THREAD_STATUSES), name="status"),
        Index("uq_aftercare_threads_request", "request_id", unique=True),
        Index("ix_aftercare_threads_tenant", "tenant_id", "last_message_at"),
    )


class AftercareMessage(Base):
    __tablename__ = "aftercare_messages"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aftercare_threads.id", ondelete="CASCADE"))
    sender: Mapped[str] = mapped_column(String(8))
    staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id", ondelete="SET NULL"))
    text_original: Mapped[str] = mapped_column(Text)  # 보낸 사람 언어
    text_translated: Mapped[str | None] = mapped_column(Text)  # 상대 언어 (번역은 ai/llm 연결 뒤)
    has_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        CheckConstraint(_in("sender", SENDERS), name="sender"),
        Index("ix_aftercare_messages_thread", "thread_id", "created_at"),
    )
