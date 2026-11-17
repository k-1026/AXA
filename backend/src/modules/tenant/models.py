"""병원 계정 (B). docs/backend-plan.md 4-2절, docs/backend-db-schema.md.

- `tenants`: 입점 병원 1곳 = 1행. **등록 외국인환자 유치의료기관만** 상담 요청을 받음 (`requests_enabled`)
- `staff_users`: 병원 직원. 직원 API는 토큰의 `tenant_id`로만 조회 (core/security.py `current_staff`)
- `hospitals` 테이블(A)이 아직 없어서 `hospital_id`는 FK 없이 둠 → hospitals가 생기면 FK 추가 (리비전은 A)
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base, utcnow

STAFF_ROLES = ("owner", "staff")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[int] = mapped_column(BigInteger)  # hospitals.id (FK는 hospitals 생긴 뒤)
    display_name: Mapped[str] = mapped_column(String(100))  # hospitals가 생기기 전까지 대시보드 표시용
    registration_no: Mapped[str | None] = mapped_column(String(40))  # 외국인환자 유치의료기관 등록번호
    requests_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 등록 기관만 True
    aftercare_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 사후관리 지원 여부 (환자 필터·요금)
    joined_at: Mapped[datetime] = mapped_column(default=utcnow)  # 입점일 (첫 3개월 구독료 무료 계산용)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (Index("uq_tenants_hospital", "hospital_id", unique=True),)


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(254))  # 소문자로 저장 (patients와 같은 규칙)
    password_hash: Mapped[str] = mapped_column(Text)  # argon2id. 로그인 API는 A (POST /auth/staff/login)
    role: Mapped[str] = mapped_column(String(10), default="staff")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    disabled_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("role IN (" + ", ".join(f"'{x}'" for x in STAFF_ROLES) + ")", name="role"),
        Index("uq_staff_users_email", "email", unique=True),
        Index("ix_staff_users_tenant", "tenant_id"),
    )
