"""환자 계정 규칙. 탈퇴하면 행을 바로 삭제 (auth.service.withdraw, 결정 15)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.patient.models import Patient
from modules.patient.schemas import PatientUpdate


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
