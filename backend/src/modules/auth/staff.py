"""병원 직원 가입·로그인 (A). 가입할 때 환자/병원 관계자를 나눔 — 병원 쪽은 입점 신청 = 병원 계정 + 대표 직원.

- 가입: 등록 유치의료기관이고 영업 중인 병원만 (`hospital.service.require_requestable`) · 병원 1곳 = 계정 1개
  (이미 입점했으면 409 `auth.hospital_taken`) · `terms`·`privacy` 동의 필수 (동의 기록은 환자용 표라 직원은 남기지 않음, 팀 확인)
- 직원 계정 테이블 `tenants`·`staff_users`는 B 모델. 여기서는 만들기·읽기만
- 로그인: 환자와 같은 규칙 (실패 응답 하나로, 시도 제한, argon2id). 직원 토큰은 세션 없이 `tenant_id`만 (contracts 3절)
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import AppError
from core.security import create_access_token
from modules.auth import attempts
from modules.auth.schemas import StaffLoginRequest, StaffSignupRequest, TokenOut
from modules.auth.service import SIGNUP_CONSENTS, _DUMMY_HASH, _email_taken, _invalid, password_hash
from modules.consent import service as consent_service
from modules.hospital import service as hospital_service
from modules.patient.service import normalize_email
from modules.tenant.models import StaffUser, Tenant


def _token(staff: StaffUser) -> TokenOut:
    return TokenOut(access_token=create_access_token(str(staff.id), "staff", tenant_id=str(staff.tenant_id)))


def signup(db: Session, data: StaffSignupRequest) -> TokenOut:
    missing = [k for k in SIGNUP_CONSENTS if k not in {c.kind for c in data.consents}]
    if missing:
        raise AppError(422, "consent.required", "가입하려면 필수 동의가 필요합니다", {"missing": missing})
    consent_service.check_versions(data.consents)
    basic = hospital_service.require_requestable(db, data.hospital_id)  # 미등록·폐업 403, 없으면 404
    email = normalize_email(data.email)
    if db.scalar(select(StaffUser.id).where(StaffUser.email == email)) is not None:
        raise _email_taken()
    if db.scalar(select(Tenant.id).where(Tenant.hospital_id == data.hospital_id)) is not None:
        raise AppError(409, "auth.hospital_taken", "이미 입점한 병원입니다 (병원 대표 계정에 문의)")
    try:
        tenant = Tenant(
            hospital_id=data.hospital_id,
            display_name=basic.name_ko,
            registration_no=data.registration_no,
            requests_enabled=True,
        )
        db.add(tenant)
        db.flush()
        staff = StaffUser(tenant_id=tenant.id, email=email, password_hash=password_hash.hash(data.password), role="owner")
        db.add(staff)
        db.commit()
    except IntegrityError:  # 동시 가입: 유일 제약(uq_tenants_hospital·uq_staff_users_email)이 막음
        db.rollback()
        raise AppError(409, "auth.hospital_taken", "이미 입점한 병원입니다 (병원 대표 계정에 문의)")
    return _token(staff)


def login(db: Session, data: StaffLoginRequest, client_ip: str | None = None) -> TokenOut:
    email = normalize_email(data.email)
    key = "staff:" + email  # 환자 로그인 실패 기록과 섞이지 않게
    attempts.check(key, client_ip)
    staff = db.scalar(select(StaffUser).where(StaffUser.email == email))
    if staff is None or staff.disabled_at is not None:
        password_hash.verify(data.password, _DUMMY_HASH)
        attempts.failed(key, client_ip)
        raise _invalid()
    ok, new_hash = password_hash.verify_and_update(data.password, staff.password_hash)
    if not ok:
        attempts.failed(key, client_ip)
        raise _invalid()
    attempts.succeeded(key)
    if new_hash:
        staff.password_hash = new_hash
        db.commit()
    return _token(staff)


def get(db: Session, staff_id: uuid.UUID) -> StaffUser | None:
    return db.get(StaffUser, staff_id)
