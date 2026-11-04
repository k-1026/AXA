"""환자 계정 (docs/backend-db-schema.md 3절). 건강정보·국적·연락처는 두지 않음 → 요청서에서만."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

LANGS = ("ko", "en", "zh-TW", "zh-CN", "vi")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # 소문자로 바꿔 저장 (citext 대신) → 대소문자만 다른 메일로 두 번 가입 X
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(Text)  # argon2id (pwdlib). 원문 저장 X
    display_name: Mapped[str | None] = mapped_column(String(30))
    preferred_lang: Mapped[str] = mapped_column(String(8), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")
    age14_confirmed_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint(
            "preferred_lang IN (" + ", ".join(f"'{x}'" for x in LANGS) + ")", name="lang"
        ),
        # 탈퇴하지 않은 계정끼리만 이메일 중복 X (탈퇴 후 같은 메일로 재가입 가능)
        Index(
            "uq_patients_email_live",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
