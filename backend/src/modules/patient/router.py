import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import PatientPrincipal, current_patient
from modules.auth import service as auth_service
from modules.auth.schemas import WithdrawRequest
from modules.patient import service
from modules.patient.schemas import PatientOut, PatientUpdate

router = APIRouter(prefix="/me", tags=["patient"])

Db = Annotated[Session, Depends(get_db)]
Me = Annotated[PatientPrincipal, Depends(current_patient)]


def patient_uuid(me: PatientPrincipal) -> uuid.UUID:
    try:
        return uuid.UUID(me.patient_id)
    except ValueError:  # 서명은 맞는데 sub가 uuid가 아님 → 로그인 다시
        raise AppError(401, "auth.required", "로그인이 필요합니다")


@router.get("", response_model=PatientOut)
def get_me(db: Db, me: Me):
    return service.get(db, patient_uuid(me))


@router.patch("", response_model=PatientOut)
def update_me(data: PatientUpdate, db: Db, me: Me):
    return service.update(db, patient_uuid(me), data)


@router.delete("", status_code=204)
def withdraw(data: WithdrawRequest, db: Db, me: Me) -> Response:
    """탈퇴. 비밀번호가 틀리면 401 auth.invalid_credentials. 성공하면 모든 기기 로그아웃."""
    auth_service.withdraw(db, patient_uuid(me), data.password)
    return Response(status_code=204)
