"""JWT 발급·검증과 로그인 의존성 (docs/backend-contracts.md 3절).

- 환자 토큰: sub=patient id, role=patient, sid=로그인 세션 id
  → current_patient()가 요청마다 DB에서 세션을 확인 (로그아웃하면 바로 401)
- 직원 토큰: sub=staff id, role=staff, tenant_id=병원 tenant id
- 병원 API는 current_staff()의 tenant_id로만 조회한다 (tenant 격리)
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from core.config import JWT_ALGORITHM, get_settings
from core.db import get_db
from core.errors import AppError

Role = Literal["patient", "staff"]


class TokenData(BaseModel):
    sub: str
    role: Role
    tenant_id: str | None = None
    sid: str | None = None


class PatientPrincipal(BaseModel):
    patient_id: str
    session_id: str


class StaffPrincipal(BaseModel):
    staff_id: str
    tenant_id: str


def token_expires_at(role: Role) -> datetime:
    settings = get_settings()
    minutes = (
        settings.jwt_staff_expire_minutes if role == "staff" else settings.jwt_patient_expire_minutes
    )
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def create_access_token(
    sub: str,
    role: Role,
    tenant_id: str | None = None,
    session_id: str | None = None,
    expires_at: datetime | None = None,
) -> str:
    if role == "staff" and not tenant_id:
        raise ValueError("직원 토큰에는 tenant_id가 필요합니다")
    if role == "patient" and tenant_id:
        raise ValueError("환자 토큰에는 tenant_id를 넣지 않습니다")
    if role == "patient" and not session_id:
        raise ValueError("환자 토큰에는 session_id가 필요합니다 (modules/auth/sessions.py)")

    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "role": role, "iat": now, "exp": expires_at or token_expires_at(role)}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return TokenData.model_validate(payload)
    except (InvalidTokenError, ValidationError):
        raise AppError(401, "auth.required", "로그인이 필요합니다")


bearer = HTTPBearer(auto_error=False)


def current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> TokenData:
    if credentials is None:
        raise AppError(401, "auth.required", "로그인이 필요합니다")
    return decode_access_token(credentials.credentials)


def current_patient(
    token: Annotated[TokenData, Depends(current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> PatientPrincipal:
    if token.role != "patient":
        raise AppError(403, "auth.forbidden", "환자 계정만 사용할 수 있습니다")
    from modules.auth.sessions import is_active  # core → auth 순환 import 방지

    if not token.sid or not is_active(db, token.sid, token.sub):
        # 로그아웃·만료된 세션, 탈퇴한 계정
        raise AppError(401, "auth.required", "로그인이 필요합니다")
    return PatientPrincipal(patient_id=token.sub, session_id=token.sid)


def current_staff(token: Annotated[TokenData, Depends(current_token)]) -> StaffPrincipal:
    if token.role != "staff" or not token.tenant_id:
        raise AppError(403, "auth.forbidden", "병원 직원 계정만 사용할 수 있습니다")
    return StaffPrincipal(staff_id=token.sub, tenant_id=token.tenant_id)
