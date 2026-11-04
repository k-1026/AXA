"""세션 만들기·확인·끝내기. core/security.current_patient()가 is_active()를 부른다."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.auth.models import AuthSession
from modules.patient.models import Patient


def create(db: Session, patient_id: uuid.UUID, expires_at: datetime) -> AuthSession:
    """commit하지 않음 (가입이면 계정·동의와 한 번에)."""
    row = AuthSession(patient_id=patient_id, expires_at=expires_at)
    db.add(row)
    db.flush()
    return row


def is_active(db: Session, session_id: str, patient_id: str) -> bool:
    """로그아웃 안 함 + 만료 전 + 토큰의 환자와 같음 + 탈퇴하지 않은 계정."""
    try:
        sid, pid = uuid.UUID(session_id), uuid.UUID(patient_id)
    except ValueError:
        return False
    found = db.scalar(
        select(AuthSession.id)
        .join(Patient, Patient.id == AuthSession.patient_id)
        .where(
            AuthSession.id == sid,
            AuthSession.patient_id == pid,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
            Patient.deleted_at.is_(None),
        )
    )
    return found is not None


def revoke(db: Session, session_id: uuid.UUID) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()


def revoke_all(db: Session, patient_id: uuid.UUID) -> None:
    """모든 기기에서 로그아웃 (탈퇴·비밀번호 변경 때 사용 예정)."""
    db.execute(
        update(AuthSession)
        .where(AuthSession.patient_id == patient_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()
