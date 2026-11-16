"""병원 공공정보 (적재 스크립트로 채움). 스키마: docs/backend-db-schema.md 2절.

행은 지우지 않는다: 재적재는 ykiho로 upsert, 없어진 병원은 status_verdict='closed' → id가 바뀌지 않음.
"""

from datetime import datetime, time

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base, utcnow

# SQLite는 BIGINT PK에 자동 증가를 붙이지 않음 → 테스트에선 INTEGER
BigID = BigInteger().with_variant(Integer(), "sqlite")


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(BigID, primary_key=True, autoincrement=True)
    ykiho: Mapped[str] = mapped_column(String(200), unique=True)
    name_ko: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    type_code: Mapped[str | None] = mapped_column(String(4))  # 심평원 종별 코드(clCd)
    type_name_ko: Mapped[str | None] = mapped_column(String(40))  # 종별 이름(clCdNm)
    sggu: Mapped[str | None] = mapped_column(String(40), index=True)
    addr_ko: Mapped[str | None] = mapped_column(String(400))
    addr_en: Mapped[str | None] = mapped_column(String(400))
    tel: Mapped[str | None] = mapped_column(String(40))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    homepage: Mapped[str | None] = mapped_column(String(400))
    # 외국인환자 유치의료기관 등록 여부 (해외진출법 제6조①). 상담·예약 요청은 이 병원만
    is_registered_facility: Mapped[bool] = mapped_column(Boolean, default=False)
    status_verdict: Mapped[str] = mapped_column(String(10), default="normal")  # normal/closed/unknown
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  # 시연용 가상 병원
    source: Mapped[str] = mapped_column(String(200))
    fetched_at: Mapped[datetime]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    hours: Mapped[list["HospitalHours"]] = relationship(
        cascade="all, delete-orphan", order_by="HospitalHours.day_order"
    )
    departments: Mapped[list["HospitalDepartment"]] = relationship(cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)  # 프론트 dept.* i18n 키
    hira_code: Mapped[str | None] = mapped_column(String(4))  # 심평원 dgsbjtCd


class HospitalDepartment(Base):
    __tablename__ = "hospital_departments"

    hospital_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True
    )
    dept_code: Mapped[str] = mapped_column(ForeignKey("departments.code"), primary_key=True)


class HospitalHours(Base):
    __tablename__ = "hospital_hours"

    hospital_id: Mapped[int] = mapped_column(
        BigID, ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[str] = mapped_column(String(3), primary_key=True)  # mon..sun
    day_order: Mapped[int] = mapped_column(Integer)  # 0=월 … 6=일 (정렬용)
    open_time: Mapped[time | None] = mapped_column(Time)
    close_time: Mapped[time | None] = mapped_column(Time)
    lunch_start: Mapped[time | None] = mapped_column(Time)
    lunch_end: Mapped[time | None] = mapped_column(Time)
    memo_ko: Mapped[str | None] = mapped_column(String(200))  # 원문 그대로 (휴무 안내 등)
    state: Mapped[str] = mapped_column(String(10))  # open/closed/unknown
    source: Mapped[str] = mapped_column(String(200))
    checked_at: Mapped[datetime]
