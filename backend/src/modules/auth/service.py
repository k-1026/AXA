"""환자 회원가입·로그인 (이메일 + 비밀번호).

- 가입: 만 14세 이상 확인 + `terms`·`privacy` 동의 필수. 계정과 동의 기록을 한 번에 저장
- 비밀번호는 argon2id 해시만 저장 (pwdlib, 결정 10)
- 로그인 실패는 이메일이 없든 비밀번호가 틀리든 같은 응답 (계정 존재 여부 숨김)
- 로그인할 때마다 세션 한 줄(auth_sessions) → 토큰 sid. 로그아웃하면 세션을 끝내 그 토큰은 바로 401
- 직원 로그인(`/auth/staff/login`)은 B의 `staff_users`가 생긴 뒤
"""

import uuid

from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from core.security import create_access_token, token_expires_at
from modules.auth import sessions
from modules.auth.schemas import LoginRequest, SignupRequest, TokenOut
from modules.consent import service as consent_service
from modules.patient import service as patient_service

SIGNUP_CONSENTS = ("terms", "privacy")

password_hash = PasswordHash.recommended()
# 없는 이메일로 로그인할 때도 해시 검증 시간을 똑같이 쓰려고 (응답 시간으로 가입 여부 추측 방지)
_DUMMY_HASH = password_hash.hash("not-a-real-password")


def signup(db: Session, data: SignupRequest) -> TokenOut:
    _check_signup(data)
    if patient_service.get_live_by_email(db, data.email) is not None:
        raise AppError(409, "auth.email_taken", "이미 가입된 이메일입니다")

    patient = patient_service.create(
        db,
        email=data.email,
        password_hash=password_hash.hash(data.password),
        display_name=data.display_name,
        preferred_lang=data.preferred_lang,
        timezone=data.timezone,
        age14_confirmed_at=utcnow(),
    )
    latest = {c.kind: c for c in data.consents}  # 같은 종류를 두 번 보내면 마지막 것만
    for c in latest.values():
        consent_service.record(db, patient.id, c.kind, c.version, data.preferred_lang)
    token = _start_session(db, patient.id)
    db.commit()
    return token


def login(db: Session, data: LoginRequest) -> TokenOut:
    patient = patient_service.get_live_by_email(db, data.email)
    if patient is None:
        password_hash.verify(data.password, _DUMMY_HASH)
        raise _invalid()
    ok, new_hash = password_hash.verify_and_update(data.password, patient.password_hash)
    if not ok:
        raise _invalid()
    if new_hash:  # 해시 설정이 바뀌었으면 새 설정으로 다시 저장
        patient.password_hash = new_hash
    token = _start_session(db, patient.id)
    db.commit()
    return token


def logout(db: Session, session_id: str) -> None:
    sessions.revoke(db, uuid.UUID(session_id))


def _start_session(db: Session, patient_id: uuid.UUID) -> TokenOut:
    expires_at = token_expires_at("patient")
    row = sessions.create(db, patient_id, expires_at)
    return TokenOut(
        access_token=create_access_token(
            str(patient_id), "patient", session_id=str(row.id), expires_at=expires_at
        )
    )


def _invalid() -> AppError:
    return AppError(401, "auth.invalid_credentials", "이메일 또는 비밀번호가 맞지 않습니다")


def _check_signup(data: SignupRequest) -> None:
    agreed = {c.kind for c in data.consents}
    missing = [k for k in SIGNUP_CONSENTS if k not in agreed]
    if not data.age14_confirmed or missing:
        raise AppError(
            422,
            "consent.required",
            "가입하려면 만 14세 이상 확인과 필수 동의가 필요합니다",
            {"age14_confirmed": data.age14_confirmed, "missing": missing},
        )
