"""동의 기록 (docs/backend-db-schema.md 3절). 동의 증명이라 탈퇴해도 CASCADE로 지우지 않음."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

KINDS = ("terms", "privacy", "health", "overseas_transfer")


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL")
    )
    # 요청서별 동의. booking_requests(B)가 생기면 FK 추가
    booking_request_id: Mapped[uuid.UUID | None]
    kind: Mapped[str] = mapped_column(String(24))
    version: Mapped[str] = mapped_column(String(16))
    lang: Mapped[str] = mapped_column(String(8))
    agreed_at: Mapped[datetime] = mapped_column(default=utcnow)
    withdrawn_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("kind IN (" + ", ".join(f"'{k}'" for k in KINDS) + ")", name="kind"),
        Index("ix_consents_patient", "patient_id"),
    )
