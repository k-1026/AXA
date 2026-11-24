"""환자 계정 규칙. 탈퇴하면 행을 바로 삭제 (auth.service.withdraw, 결정 15)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.patient.models import Patient
from core.db import utcnow
from modules.patient.schemas import PatientUpdate, ResidencyIn


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> Patient | None:
    return db.scalar(select(Patient).where(Patient.email == normalize_email(email)))


def get(db: Session, patient_id: uuid.UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise AppError(404, "not_found", "계정이 없습니다")
    return patient


def create(
    db: Session,
    email: str,
    password_hash: str,
    preferred_lang: str,
    timezone: str,
    age14_confirmed_at: datetime,
    display_name: str | None = None,
    residency: ResidencyIn | None = None,
) -> Patient:
    """commit하지 않음 (동의 기록과 한 번에)."""
    patient = Patient(
        email=normalize_email(email),
        password_hash=password_hash,
        display_name=display_name,
        preferred_lang=preferred_lang,
        timezone=timezone,
        age14_confirmed_at=age14_confirmed_at,
    )
    if residency is not None:
        _apply_residency(patient, residency)
    db.add(patient)
    db.flush()
    return patient


def update(db: Session, patient_id: uuid.UUID, data: PatientUpdate) -> Patient:
    patient = get(db, patient_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("preferred_lang", "timezone"):  # 필수 칸은 null로 지울 수 없음
        if field in changes and changes[field] is None:
            raise AppError(422, "validation", f"{field}는 비울 수 없습니다", {"field": field})
    for field, value in changes.items():
        setattr(patient, field, value)
    db.commit()
    return patient


def _apply_residency(patient: Patient, data: ResidencyIn) -> None:
    patient.residency = data.residency()
    patient.residence_country = data.country
    patient.residency_answered_at = utcnow()


def set_residency(db: Session, patient_id: uuid.UUID, data: ResidencyIn) -> Patient:
    """PUT /me/residency — 가입 때 답하지 않았거나 체류 상태가 바뀌었을 때."""
    patient = get(db, patient_id)
    _apply_residency(patient, data)
    db.commit()
    return patient


def require_short_term(db: Session, patient_id: uuid.UUID) -> Patient:
    """예약 요청 전 확인. 답이 없으면 422 `residency.required`, 국내 거주면 403 `residency.not_eligible`."""
    patient = get(db, patient_id)
    if patient.residency is None:
        raise AppError(422, "residency.required", "체류 형태를 먼저 알려 주세요")
    if patient.residency != "short_term":
        raise AppError(403, "residency.not_eligible", "국내 거주 외국인은 상담·예약 요청을 할 수 없습니다")
    return patient
