from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import PatientPrincipal, current_patient, patient_uuid
from modules.auth import service as auth_service
from modules.auth.attempts import client_ip
from modules.auth.schemas import WithdrawRequest
from modules.patient import service
from modules.patient.schemas import PatientOut, PatientUpdate, ResidencyIn

router = APIRouter(prefix="/me", tags=["patient"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


@router.get("", response_model=PatientOut)
def get_me(db: Db, me: Me):
    return service.get(db, patient_uuid(me))


@router.patch("", response_model=PatientOut)
def update_me(data: PatientUpdate, db: Db, me: Me):
    return service.update(db, patient_uuid(me), data)


@router.put("/residency", response_model=PatientOut)
def set_residency(data: ResidencyIn, db: Db, me: Me):
    """체류 형태 3문항 다시 답하기 (가입 때 안 했거나 바뀌었을 때). 국내 거주면 정보 열람만 (결정 28)."""
    return service.set_residency(db, patient_uuid(me), data)


@router.delete("", status_code=204)
def withdraw(data: WithdrawRequest, db: Db, me: Me, request: Request) -> Response:
    """탈퇴. 비밀번호가 틀리면 401 auth.invalid_credentials, 너무 많이 틀리면 429 auth.too_many_attempts.
    성공하면 모든 기기 로그아웃."""
    auth_service.withdraw(db, patient_uuid(me), data.password, client_ip(request))
    return Response(status_code=204)
