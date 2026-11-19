from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.db import get_db
from core.errors import AppError
from modules.hospital import service
from modules.hospital.schemas import HospitalDetail, HospitalListItem

router = APIRouter(tags=["hospitals"])


@router.get("/hospitals", response_model=list[HospitalListItem])
def list_hospitals(
    db: Annotated[Session, Depends(get_db)],
    sggu: str | None = None,
    dept: str | None = None,
    registered: bool | None = None,
    open_on: Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"] | None = None,
    ids: Annotated[str | None, Query(description="쉼표로 구분한 병원 id (조회 기록용)")] = None,
    sort: Literal["name", "distance"] = "name",
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
):
    """로그인 없이. **등록 유치의료기관만** (결정 21) + 요청 가능(`can_request` = 등록 + 영업 중).

    정렬은 `name`·`distance`만 (그 밖은 422). 등록·요금제 여부로 순서를 바꾸지 않음.
    """
    id_list = None
    if ids is not None:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()][:100]
        except ValueError:
            raise AppError(422, "validation", "ids는 숫자 목록입니다", {"fields": ["ids"]}) from None
    return service.list_hospitals(
        db, sggu=sggu, dept=dept, registered=registered, open_on=open_on, ids=id_list, sort=sort, lat=lat, lng=lng
    )


@router.get("/hospitals/{hospital_id}", response_model=HospitalDetail)
def get_hospital(hospital_id: int, db: Annotated[Session, Depends(get_db)]):
    """로그인 없이. 상세 + 진료시간 + 출처·수집일. 미등록 병원은 없는 병원과 같은 404 (결정 21)."""
    return service.get_detail(db, hospital_id)
