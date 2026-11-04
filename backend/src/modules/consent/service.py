"""동의 기록·확인 (docs/backend-contracts.md 5절). B도 require()를 호출한다.

record()는 commit하지 않음 → 호출한 쪽이 계정 생성·요청서 저장과 한 번에 commit
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.consent.models import Consent
from modules.consent.schemas import ConsentOut


def record(
    db: Session,
    patient_id: uuid.UUID,
    kind: str,
    version: str,
    lang: str,
    request_id: uuid.UUID | None = None,
) -> ConsentOut:
    row = Consent(
        patient_id=patient_id, kind=kind, version=version, lang=lang, booking_request_id=request_id
    )
    db.add(row)
    db.flush()
    return ConsentOut.model_validate(row)


def require(
    db: Session,
    patient_id: uuid.UUID,
    kinds: list[str],
    request_id: uuid.UUID | None = None,
) -> None:
    """철회하지 않은 동의가 kinds 전부 있는지. request_id를 주면 그 요청서에 대한 동의만 인정."""
    stmt = select(Consent.kind).where(
        Consent.patient_id == patient_id,
        Consent.kind.in_(kinds),
        Consent.withdrawn_at.is_(None),
    )
    if request_id is not None:
        stmt = stmt.where(Consent.booking_request_id == request_id)
    have = set(db.scalars(stmt))
    missing = [k for k in kinds if k not in have]
    if missing:
        raise AppError(422, "consent.required", "필수 동의가 없습니다", {"missing": missing})
