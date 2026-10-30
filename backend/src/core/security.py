"""JWT 발급·검증과 로그인 의존성 (docs/backend-contracts.md 3절).

- 환자 토큰: sub=patient id, role=patient
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

from core.config import get_settings
from core.errors import AppError

Role = Literal["patient", "staff"]


class TokenData(BaseModel):
    sub: str
    role: Role
    tenant_id: str | None = None


class PatientPrincipal(BaseModel):
    patient_id: str


class StaffPrincipal(BaseModel):
    staff_id: str
    tenant_id: str


def create_access_token(sub: str, role: Role, tenant_id: str | None = None) -> str:
    if role == "staff" and not tenant_id:
        raise ValueError("직원 토큰에는 tenant_id가 필요합니다")
    if role == "patient" and tenant_id:
        raise ValueError("환자 토큰에는 tenant_id를 넣지 않습니다")

    settings = get_settings()
    minutes = (
        settings.jwt_staff_expire_minutes if role == "staff" else settings.jwt_patient_expire_minutes
    )
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "role": role, "iat": now, "exp": now + timedelta(minutes=minutes)}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenData:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
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


def current_patient(token: Annotated[TokenData, Depends(current_token)]) -> PatientPrincipal:
    if token.role != "patient":
        raise AppError(403, "auth.forbidden", "환자 계정만 사용할 수 있습니다")
    return PatientPrincipal(patient_id=token.sub)


def current_staff(token: Annotated[TokenData, Depends(current_token)]) -> StaffPrincipal:
    if token.role != "staff" or not token.tenant_id:
        raise AppError(403, "auth.forbidden", "병원 직원 계정만 사용할 수 있습니다")
    return StaffPrincipal(staff_id=token.sub, tenant_id=token.tenant_id)
