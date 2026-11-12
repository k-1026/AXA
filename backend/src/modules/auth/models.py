"""로그인 세션. 토큰의 `sid` = 이 테이블의 id. 로그아웃하면 revoked_at → 그 토큰은 바로 401."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]  # 토큰 exp와 같음. 지난 줄은 정기 삭제
    revoked_at: Mapped[datetime | None]  # 로그아웃 시각

    __table_args__ = (
        Index("ix_auth_sessions_patient", "patient_id"),
        Index("ix_auth_sessions_expires", "expires_at"),
    )
