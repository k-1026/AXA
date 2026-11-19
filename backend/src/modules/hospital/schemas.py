from datetime import datetime, time

from pydantic import BaseModel, ConfigDict


class HospitalBasic(BaseModel):
    """다른 모듈(B 대시보드 등)이 `get_basic()`으로 받는 기본 정보."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ykiho: str
    name_ko: str
    name_en: str | None
    type_code: str | None
    sggu: str | None
    addr_ko: str | None
    tel: str | None
    is_registered_facility: bool
    is_demo: bool
    # 상담·예약 요청 가능 = 등록 유치의료기관 + 영업 중 (compliance 2-1, 해외진출법 제24조①3)
    can_request: bool


class HospitalListItem(HospitalBasic):
    type_name_ko: str | None
    lat: float | None
    lng: float | None
    departments: list[str]
    distance_km: float | None = None  # sort=distance일 때만


class HoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: str
    state: str  # open/closed/unknown
    open_time: time | None
    close_time: time | None
    lunch_start: time | None
    lunch_end: time | None
    memo_ko: str | None
    # 요일마다 출처가 다를 수 있음: 심평원 API / 직접 채운 값(병원 홈페이지 URL 등)
    source: str
    checked_at: datetime


class HospitalDetail(HospitalListItem):
    addr_en: str | None
    homepage: str | None
    status_verdict: str
    hours: list[HoursOut]
    source: str
    fetched_at: datetime
