from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import PatientPrincipal, current_patient
from modules.auth import service, staff
from modules.auth.attempts import client_ip
from modules.auth.schemas import LoginRequest, SignupRequest, StaffLoginRequest, StaffSignupRequest, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[Session, Depends(get_db)]


@router.post("/patient/signup", response_model=TokenOut, status_code=201)
def signup(data: SignupRequest, db: Db):
    """회원가입 → 바로 로그인된 토큰."""
    return service.signup(db, data)


@router.post("/patient/login", response_model=TokenOut)
def login(data: LoginRequest, db: Db, request: Request):
    """실패가 많으면 429 auth.too_many_attempts (detail.retry_after 초)."""
    return service.login(db, data, client_ip(request))


@router.post("/patient/logout", status_code=204)
def logout(db: Db, me: Annotated[PatientPrincipal, Depends(current_patient)]) -> Response:
    """이 토큰의 세션을 끝냄 → 같은 토큰으로 부르면 바로 401. 다른 기기 로그인은 그대로."""
    service.logout(db, me.session_id)
    return Response(status_code=204)


@router.post("/staff/signup", response_model=TokenOut, status_code=201)
def staff_signup(data: StaffSignupRequest, db: Db):
    """입점 병원 가입 (병원 관계자) → 병원 계정 + 대표 직원, 바로 직원 토큰."""
    return staff.signup(db, data)


@router.post("/staff/login", response_model=TokenOut)
def staff_login(data: StaffLoginRequest, db: Db, request: Request):
    """직원 로그인. 실패가 많으면 429 auth.too_many_attempts."""
    return staff.login(db, data, client_ip(request))
