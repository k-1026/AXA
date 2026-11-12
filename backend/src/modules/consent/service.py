"""동의 기록·확인 (docs/backend-contracts.md 5절). B도 require()를 호출한다.

record()는 commit하지 않음 → 호출한 쪽이 계정 생성·요청서 저장과 한 번에 commit
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.errors import AppError
from modules.consent.models import Consent
from modules.consent.schemas import ConsentIn, ConsentOut

# 지금 화면에 보여 주는 동의 문서 버전 = 프론트 문서의 개정일
# (apps/web-platform/src/features/legal/terms.ts·privacy.ts의 `updated`). 문서를 고치면 둘 다 바꿀 것 (테스트가 확인)
# health·overseas_transfer는 아직 기준 문서가 없어 검사하지 않음
CURRENT_VERSIONS = {"terms": "2026-11-03", "privacy": "2026-11-03"}


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


def check_versions(consents: list[ConsentIn]) -> None:
    """현재 버전이 정해진 종류는 그 버전만 받음 → 아니면 422 validation (detail.invalid)."""
    invalid = [
        {"kind": c.kind, "version": c.version, "current": CURRENT_VERSIONS[c.kind]}
        for c in consents
        if c.kind in CURRENT_VERSIONS and c.version != CURRENT_VERSIONS[c.kind]
    ]
    if invalid:
        raise AppError(422, "validation", "동의 문서 버전이 맞지 않습니다 (화면을 새로 고침)", {"invalid": invalid})


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


def detach_patient(db: Session, patient_id: uuid.UUID) -> None:
    """탈퇴할 때: 동의 기록은 증명용으로 남기고 누구 것인지(patient_id)만 비움. commit하지 않음."""
    db.execute(update(Consent).where(Consent.patient_id == patient_id).values(patient_id=None))
