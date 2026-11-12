"""세션 만들기·확인·끝내기. core/security.current_patient()가 is_active()를 부른다.

여기 함수는 모두 commit하지 않는다 → 부르는 쪽(auth.service 등)이 다른 변경과 한 번에 commit.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from core.db import utcnow
from modules.auth.models import AuthSession


def create(db: Session, patient_id: uuid.UUID, expires_at: datetime) -> AuthSession:
    """가입이면 계정·동의와 한 번에 commit."""
    row = AuthSession(patient_id=patient_id, expires_at=expires_at)
    db.add(row)
    db.flush()
    return row


def is_active(db: Session, session_id: str, patient_id: str) -> bool:
    """로그아웃 안 함 + 만료 전 + 토큰의 환자와 같음. 탈퇴하면 세션 행이 지워져 False."""
    try:
        sid, pid = uuid.UUID(session_id), uuid.UUID(patient_id)
    except ValueError:
        return False
    found = db.scalar(
        select(AuthSession.id).where(
            AuthSession.id == sid,
            AuthSession.patient_id == pid,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
    )
    return found is not None


def revoke(db: Session, session_id: uuid.UUID) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def revoke_all(db: Session, patient_id: uuid.UUID) -> None:
    """모든 기기에서 로그아웃 (탈퇴·비밀번호 변경 때 사용 예정)."""
    db.execute(
        update(AuthSession)
        .where(AuthSession.patient_id == patient_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def delete_all(db: Session, patient_id: uuid.UUID) -> None:
    """탈퇴할 때 그 환자의 세션 행 전부 삭제."""
    db.execute(delete(AuthSession).where(AuthSession.patient_id == patient_id))


def purge_dead(db: Session, patient_id: uuid.UUID | None = None) -> int:
    """만료됐거나 로그아웃한 세션 행 삭제 (다시 쓸 일 없음).

    - 로그인할 때 그 환자 것만 정리 (auth.service._start_session)
    - patient_id=None이면 전체 → 매일 정리 (maintenance.service.purge, POST /internal/purge)
    - 행이 없으면 is_active()가 False라 지워도 로그인 상태는 그대로
    """
    stmt = delete(AuthSession).where(
        or_(AuthSession.expires_at <= utcnow(), AuthSession.revoked_at.is_not(None))
    )
    if patient_id is not None:
        stmt = stmt.where(AuthSession.patient_id == patient_id)
    return db.execute(stmt).rowcount
