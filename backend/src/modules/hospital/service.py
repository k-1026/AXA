"""병원 정보 규칙.

- 정보(목록·지도·상세)는 모든 병원에 대해 준다 (팀 결정 2026-11-16: 전체 병원 + 등록 표시)
- 상담·예약 요청은 `can_request`인 병원만: 등록 유치의료기관 + 영업 중 (시연용 가상 병원은 시드 만들 때 추가)
  (해외진출법 제24조①3: 유치사업자가 미등록 의료기관에 소개·알선하면 등록 취소 사유)
- 정렬은 거리·이름만. 등록·요청 가능·요금제 여부로 순서를 바꾸지 않음 (AGENTS.md 6절)
"""

import math
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.errors import AppError
from modules.hospital.models import Hospital, HospitalDepartment
from modules.hospital.schemas import HospitalBasic, HospitalDetail, HospitalListItem, HoursOut


def can_request(h: Hospital) -> bool:
    return h.status_verdict == "normal" and h.is_registered_facility


def _basic_fields(h: Hospital) -> dict:
    return {
        "id": h.id,
        "ykiho": h.ykiho,
        "name_ko": h.name_ko,
        "name_en": h.name_en,
        "type_code": h.type_code,
        "sggu": h.sggu,
        "addr_ko": h.addr_ko,
        "tel": h.tel,
        "is_registered_facility": h.is_registered_facility,
        "is_demo": h.is_demo,
        "can_request": can_request(h),
    }


def _list_item(h: Hospital) -> HospitalListItem:
    return HospitalListItem(
        **_basic_fields(h),
        type_name_ko=h.type_name_ko,
        lat=h.lat,
        lng=h.lng,
        departments=sorted(d.dept_code for d in h.departments),
    )


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """직선거리 (하버사인)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def list_hospitals(
    db: Session,
    *,
    sggu: str | None = None,
    dept: str | None = None,
    registered: bool | None = None,
    ids: list[int] | None = None,
    sort: Literal["name", "distance"] = "name",
    lat: float | None = None,
    lng: float | None = None,
) -> list[HospitalListItem]:
    """영업 중(normal)·미확인(unknown) 병원. 폐업(closed)은 빼고, `ids`로 부를 때만 포함."""
    if sort == "distance" and (lat is None or lng is None):
        raise AppError(422, "validation", "거리순 정렬에는 lat·lng가 필요합니다", {"fields": ["lat", "lng"]})

    q = select(Hospital).options(selectinload(Hospital.departments))
    if ids is not None:
        q = q.where(Hospital.id.in_(ids))  # 조회 기록 화면: 폐업했어도 기본 정보는 보여 줌
    else:
        q = q.where(Hospital.status_verdict != "closed")
    if sggu:
        q = q.where(Hospital.sggu == sggu)
    if dept:
        q = q.where(
            Hospital.id.in_(select(HospitalDepartment.hospital_id).where(HospitalDepartment.dept_code == dept))
        )
    if registered is not None:
        q = q.where(Hospital.is_registered_facility.is_(registered))

    items = [_list_item(h) for h in db.scalars(q.order_by(Hospital.name_ko, Hospital.id))]
    if sort == "distance":
        for it in items:
            if it.lat is not None and it.lng is not None:
                it.distance_km = round(_km(lat, lng, it.lat, it.lng), 2)
        items.sort(key=lambda it: (it.distance_km is None, it.distance_km or 0.0))
    return items


def _get(db: Session, hospital_id: int) -> Hospital:
    h = db.get(Hospital, hospital_id)
    if h is None:
        raise AppError(404, "not_found", "병원을 찾을 수 없습니다")
    return h


def get_detail(db: Session, hospital_id: int) -> HospitalDetail:
    """폐업 병원도 상세는 보여 줌 (찜·조회 기록에서 들어올 수 있음). 요청 가능 여부는 can_request로."""
    h = _get(db, hospital_id)
    return HospitalDetail(
        **_list_item(h).model_dump(),
        addr_en=h.addr_en,
        homepage=h.homepage,
        status_verdict=h.status_verdict,
        hours=[HoursOut.model_validate(x) for x in h.hours],
        source=h.source,
        fetched_at=h.fetched_at,
    )


def get_basic(db: Session, hospital_id: int) -> HospitalBasic:
    """contracts 5절: B(대시보드)·A(요청서 제출)가 부름. 요청서 API는 `can_request`가 false면 막는다."""
    return HospitalBasic(**_basic_fields(_get(db, hospital_id)))
