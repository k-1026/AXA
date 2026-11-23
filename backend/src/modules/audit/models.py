"""열람·처리 기록 (B 모듈, A 작성 · B 확인). dashboard-integration 5-3: 건강정보는 해당 병원 직원만 + 열람 기록.

- 누가(`actor` = 직원 id 문자열), 어느 병원(`tenant_id`)에서, 무엇을(`action`), 어떤 대상(`ref` = "종류:id")
- 내용(메시지 글·사진)은 넣지 않음 → 기록 자체가 건강정보가 되지 않게
"""

from datetime import datetime
import uuid

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

BigIntId = BigInteger().with_variant(Integer(), "sqlite")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigIntId, Identity(), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    actor: Mapped[str] = mapped_column(String(64))  # 직원 id (직원 행이 지워져도 기록은 남게 FK 없음)
    action: Mapped[str] = mapped_column(String(40))
    ref: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (Index("ix_audit_logs_tenant", "tenant_id", "created_at"),)
