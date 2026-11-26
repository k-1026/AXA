"""챗봇 병원 찾기·상세(`ToolContext.hospitals`)의 백엔드 구현 — 실제 병원 DB를 `hospital.service`로만 읽는다.

결과는 챗봇 카드 형식(`ai/agent/schemas.py` HospitalBrief·HospitalDetailData)에 맞춘 dict.
- 진료과는 카드에 한국어 이름으로 (가상 병원 데이터와 같게), 지역은 "대구" 뺀 구·군 이름
- 응대 언어 정보는 공공데이터에 없음 → `staff_languages = []`, `ai_translation_chat = False` (병원에 확인 안내는 도구가)
- 공개는 등록 병원만 (결정 21, `hospital.service`가 거름) → `registered_only=False`여도 미등록 병원은 안 나옴, 상세는 None
- 상담 요청 가능 = `can_request` (등록 유치의료기관 + 영업 중)
- 조건 맞춤 제안·예약은 **가상 병원만** (2026-11-17 결정, 결정 31): DB의 `is_demo` 병원 중 입점(요청 받기 켬)한 곳.
  응대 언어는 가상 병원 목록 파일(`data/processed/demo/demo_hospitals.json`)의 지어낸 값. 실제 병원은 찾기·상세만
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.agent.session_store import JSON
from ai.agent.tools.chat_tools import DEPT_CODES
from core.errors import AppError
from modules.hospital import service as hospital_service
from modules.hospital.models import Hospital
from modules.tenant.models import Tenant

DEMO_FILE = Path(__file__).resolve().parents[4] / "data" / "processed" / "demo" / "demo_hospitals.json"


@lru_cache
def _demo_extra() -> dict[int, dict]:
    """가상 병원 id → {staff_languages, ai_translation_chat}. 파일이 없으면 빈 값 (언어 정보 없음으로)."""
    try:
        rows = json.loads(DEMO_FILE.read_text(encoding="utf-8"))["hospitals"]
    except (OSError, ValueError, KeyError):
        return {}
    return {h["id"]: {"staff_languages": h.get("staff_languages", []), "ai_translation_chat": h.get("ai_translation_chat", False)}
            for h in rows}

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


def _lunch(rows) -> dict[str, str]:
    """요일별 점심시간 "HH:MM-HH:MM" (진료하는 날 중 점심 정보가 있는 날만). 챗봇 초안이 서버 요청서 검사(_check_open)와
    같은 기준으로 점심시간도 막게 (11/26 — 13:30 같은 점심 시간은 초안이 만들어진 뒤 제출 때 422가 났음)."""
    return {x.day: f"{x.lunch_start:%H:%M}-{x.lunch_end:%H:%M}" for x in rows
            if x.state == "open" and x.lunch_start is not None and x.lunch_end is not None}


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

    def _detail(self, hospital_id: int):
        try:
            return hospital_service.get_detail(self.db, hospital_id)
        except AppError as e:
            if e.code == "not_found":
                return None
            raise

    def get(self, hospital_id: int, d=None) -> JSON | None:
        d = d or self._detail(hospital_id)
        if d is None:
            return None
        return {
            **_brief(d),
            "hours": _hours(d.hours),
            "address_en": d.addr_en or d.addr_ko or "",
            "tel": d.tel or "",
            "hours_source": f"{SOURCE_NOTE}, fetched {d.fetched_at:%Y-%m-%d}",
            "can_request_consultation": d.can_request,
        }

    # ---------- 조건 맞춤 제안·예약 = 가상 병원만 (결정 31) ----------

    def _accepting_demo_ids(self) -> list[int]:
        """`is_demo` + 등록 + 입점(요청 받기 켬)한 병원 id."""
        return list(self.db.scalars(
            select(Hospital.id).join(Tenant, Tenant.hospital_id == Hospital.id)
            .where(Hospital.is_demo.is_(True), Hospital.is_registered_facility.is_(True), Tenant.requests_enabled.is_(True))
            .order_by(Hospital.id)
        ))

    def booking_info(self, hospital_id: int) -> JSON | None:
        """예약 도구용 (가상 병원 데이터와 같은 모양). 없으면 None. `accepts_requests` = 메디대구로 요청을 받는 병원."""
        detail = self._detail(hospital_id)
        if detail is None:
            return None
        d = self.get(hospital_id, detail)
        extra = _demo_extra().get(hospital_id, {})
        return {
            "id": d["hospital_id"], "name_ko": d["name_ko"], "name_en": d["name_en"], "district": d["district"],
            "departments": d["departments"], "is_registered_facility": d["is_registered_facility"],
            "staff_languages": extra.get("staff_languages", []), "ai_translation_chat": extra.get("ai_translation_chat", False),
            "hours": d["hours"], "lunch": _lunch(detail.hours), "address_en": d["address_en"], "tel": d["tel"],
            "accepts_requests": hospital_id in self._accepting_demo_ids(),
        }

    def demo_candidates(self, dept_code: str, district: str | None = None) -> list[JSON]:
        """조건 맞춤 제안 후보: 그 진료과가 있는 가상 입점 병원 (예약 도구용 모양)."""
        out = []
        for hid in self._accepting_demo_ids():
            h = self.booking_info(hid)
            if h and DEPT_KO.get(dept_code, dept_code) in h["departments"] and (not district or h["district"] == district):
                out.append(h)
        return out
