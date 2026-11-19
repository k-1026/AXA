"""챗봇 병원 찾기·상세(`ToolContext.hospitals`)의 백엔드 구현 — 실제 병원 DB를 `hospital.service`로만 읽는다.

결과는 챗봇 카드 형식(`ai/agent/schemas.py` HospitalBrief·HospitalDetailData)에 맞춘 dict.
- 진료과는 카드에 한국어 이름으로 (가상 병원 데이터와 같게), 지역은 "대구" 뺀 구·군 이름
- 응대 언어 정보는 공공데이터에 없음 → `staff_languages = []`, `ai_translation_chat = False` (병원에 확인 안내는 도구가)
- 공개는 등록 병원만 (결정 21, `hospital.service`가 거름) → `registered_only=False`여도 미등록 병원은 안 나옴, 상세는 None
- 상담 요청 가능 = `can_request` (등록 유치의료기관 + 영업 중)
- 조건 맞춤 제안·예약은 아직 가상 병원 (2026-11-17 결정: 찾기·상세만 연결)
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ai.agent.session_store import JSON
from ai.agent.tools.chat_tools import DEPT_CODES
from core.errors import AppError
from modules.hospital import service as hospital_service

SOURCE_NOTE = "public data (HIRA hospital info service)"
DEPT_KO = {code: ko for ko, code in DEPT_CODES.items()}


def _district(sggu: str | None) -> str:
    return (sggu or "").removeprefix("대구")


def _brief(h) -> JSON:
    return {
        "hospital_id": h.id,
        "name_ko": h.name_ko,
        "name_en": h.name_en or h.name_ko,  # 영문 이름은 등록 병원 자료에만 있음
        "district": _district(h.sggu),
        "departments": [DEPT_KO.get(d, d) for d in h.departments],
        "is_registered_facility": h.is_registered_facility,
        "staff_languages": [],
        "ai_translation_chat": False,
    }


def _hours(rows) -> dict[str, str | None]:
    """카드 규칙: 값 = 진료 시간, None = 휴진. 시간 정보가 없는 요일(unknown)은 휴진으로 보이지 않게 **빼 둔다**."""
    out: dict[str, str | None] = {}
    for x in rows:
        if x.state == "open":
            out[x.day] = f"{x.open_time:%H:%M}-{x.close_time:%H:%M}"
        elif x.state == "closed":
            out[x.day] = None
    return out


class HospitalGateway:
    def __init__(self, db: Session):
        self.db = db

    def search(self, *, dept_code: str, district: str | None, registered_only: bool, open_on: str | None,
               limit: int) -> JSON:
        rows = hospital_service.list_hospitals(
            self.db, dept=dept_code, sggu=f"대구{district}" if district else None,
            registered=True if registered_only else None, open_on=open_on,
        )
        return {"count": len(rows), "hospitals": [_brief(h) for h in rows[:limit]]}

    def get(self, hospital_id: int) -> JSON | None:
        try:
            d = hospital_service.get_detail(self.db, hospital_id)
        except AppError as e:
            if e.code == "not_found":
                return None
            raise
        return {
            **_brief(d),
            "hours": _hours(d.hours),
            "address_en": d.addr_en or d.addr_ko or "",
            "tel": d.tel or "",
            "hours_source": f"{SOURCE_NOTE}, fetched {d.fetched_at:%Y-%m-%d}",
            "can_request_consultation": d.can_request,
        }
