import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from core.security import PatientPrincipal, current_patient
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
    return service.get_live(db, patient_uuid(me))


@router.patch("", response_model=PatientOut)
def update_me(data: PatientUpdate, db: Db, me: Me):
    return service.update(db, patient_uuid(me), data)
