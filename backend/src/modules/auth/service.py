"""환자 회원가입·로그인 (이메일 + 비밀번호).

- 가입: 만 14세 이상 확인 + `terms`·`privacy` 동의 필수. 계정과 동의 기록을 한 번에 저장
- 비밀번호는 argon2id 해시만 저장 (pwdlib, 결정 10)
- 로그인 실패는 이메일이 없든 비밀번호가 틀리든 같은 응답 (계정 존재 여부 숨김)
- 실패가 많으면 429 auth.too_many_attempts (attempts.py: 이메일당·IP당). 탈퇴 비밀번호 확인도 같음
- 로그인할 때마다 세션 한 줄(auth_sessions) → 토큰 sid. 로그아웃하면 세션을 끝내 그 토큰은 바로 401
- 직원 로그인(`/auth/staff/login`)은 B의 `staff_users`가 생긴 뒤
"""

import uuid

from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db import utcnow
from core.errors import AppError
from core.security import create_access_token, token_expires_at
from modules.auth import attempts, sessions
from modules.auth.schemas import LoginRequest, SignupRequest, TokenOut
from modules.chatbot import sessions as chat_sessions
from modules.consent import service as consent_service
from modules.patient import service as patient_service

SIGNUP_CONSENTS = ("terms", "privacy")

password_hash = PasswordHash.recommended()
# 없는 이메일로 로그인할 때도 해시 검증 시간을 똑같이 쓰려고 (응답 시간으로 가입 여부 추측 방지)
_DUMMY_HASH = password_hash.hash("not-a-real-password")


def signup(db: Session, data: SignupRequest) -> TokenOut:
    _check_signup(data)
    if patient_service.get_by_email(db, data.email) is not None:
        raise _email_taken()

    hashed = password_hash.hash(data.password)
    try:
        patient = patient_service.create(
            db,
            email=data.email,
            password_hash=hashed,
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
    except IntegrityError:
        # 같은 메일 동시 가입: 둘 다 위 확인을 지나면 DB 유일 제약(uq_patients_email)이 막음
        db.rollback()
        raise _email_taken()
    return token


def login(db: Session, data: LoginRequest, client_ip: str | None = None) -> TokenOut:
    email = patient_service.normalize_email(data.email)
    attempts.check(email, client_ip)
    patient = patient_service.get_by_email(db, email)
    if patient is None:
        password_hash.verify(data.password, _DUMMY_HASH)
        attempts.failed(email, client_ip)
        raise _invalid()
    ok, new_hash = password_hash.verify_and_update(data.password, patient.password_hash)
    if not ok:
        attempts.failed(email, client_ip)
        raise _invalid()
    attempts.succeeded(email)
    if new_hash:  # 해시 설정이 바뀌었으면 새 설정으로 다시 저장
        patient.password_hash = new_hash
    token = _start_session(db, patient.id)
    db.commit()
    return token


def withdraw(db: Session, patient_id: uuid.UUID, password: str, client_ip: str | None = None) -> None:
    """탈퇴: 비밀번호 확인 → 계정 행을 바로 삭제 (결정 15). 되돌릴 수 없음

    - 세션 전부 삭제 → 모든 기기에서 그 토큰은 바로 401
    - 챗봇 대화(메시지 포함)도 전부 삭제 (최소 저장 결정: 탈퇴하면 즉시 삭제)
    - 동의 기록은 동의 증명이라 남기되 patient_id를 비움 (누구 것인지 알 수 없게, 스키마 3절)
    - DB의 FK(CASCADE·SET NULL)에 기대지 않고 직접 지움 (SQLite 테스트에서도 같게)
    - 같은 메일로 바로 다시 가입 가능
    - 비밀번호 실패는 로그인과 같은 시도 제한 (같은 이메일 기록) → 토큰을 가진 사람이 비밀번호를 맞춰 보지 못하게
    """
    patient = patient_service.get(db, patient_id)
    attempts.check(patient.email, client_ip)
    if not password_hash.verify(password, patient.password_hash):
        attempts.failed(patient.email, client_ip)
        raise _invalid()
    sessions.delete_all(db, patient.id)
    chat_sessions.delete_all(db, patient.id)  # 챗봇 대화도 즉시 삭제
    consent_service.detach_patient(db, patient.id)
    db.delete(patient)
    db.commit()


def logout(db: Session, session_id: str) -> None:
    sessions.revoke(db, uuid.UUID(session_id))
    db.commit()


def _start_session(db: Session, patient_id: uuid.UUID) -> TokenOut:
    sessions.purge_dead(db, patient_id)  # 쌓이지 않게 이 환자의 죽은 세션 정리
    expires_at = token_expires_at("patient")
    row = sessions.create(db, patient_id, expires_at)
    return TokenOut(
        access_token=create_access_token(
            str(patient_id), "patient", session_id=str(row.id), expires_at=expires_at
        )
    )


def _email_taken() -> AppError:
    return AppError(409, "auth.email_taken", "이미 가입된 이메일입니다")


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
