"""가짜 예약 저장소 — 백엔드 `booking.service`(docs/backend-contracts.md 5·6절)가 올라오기 전까지 6단계 시연용.

백엔드가 생기면 이 파일의 함수 이름은 그대로 두고 안쪽만 `booking.service.create_request` 등으로 바꾼다.
같은 규칙을 코드로 먼저 지켜 둔다:
- 제출은 **로그인한 환자**만 (`auth.required`), 환자가 [제출] 버튼을 눌렀을 때만 (챗봇 도구로는 제출하지 않음)
- 필수 동의가 없으면 거절 (`consent.required`): privacy 필수, health·overseas_transfer 조건부
- 같은 병원에 처리 안 된 요청(pending·proposed)이 있으면 거절 (`booking.duplicate`)
- 국내 거주자·미등록 병원은 거절
- 상태: pending → confirmed / rejected / proposed, proposed → confirmed(환자 수락), pending·proposed → cancelled(환자 취소)

시간: 병원 시간대(KST, 한국은 서머타임 없음) 문자열 "YYYY-MM-DD HH:MM" → UTC ISO로 바꿔 저장 (계약: preferred_slots는 UTC).
"""

from __future__ import annotations

import copy
import itertools
from datetime import datetime, timedelta, timezone
from typing import Any

from ai.agent.tools import fake_data as fd

JSON = dict[str, Any]
KST = timezone(timedelta(hours=9))
OPEN_STATUSES = ("pending", "proposed")
TRANSITIONS = {  # (현재 상태, 행동) → 다음 상태. 행동 주체: hospital 또는 patient
    ("pending", "confirm"): "confirmed",
    ("pending", "reject"): "rejected",
    ("pending", "propose"): "proposed",
    ("proposed", "accept"): "confirmed",  # 환자
    ("pending", "cancel"): "cancelled",  # 환자
    ("proposed", "cancel"): "cancelled",  # 환자
}


class BookingError(Exception):
    """코드는 docs/backend-contracts.md 4절 에러 코드와 같다."""

    def __init__(self, code: str, message: str, detail: JSON | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}

    def as_dict(self) -> JSON:
        return {"code": self.code, "message": self.message, "detail": self.detail}


def parse_local_slot(text: str) -> datetime:
    """'YYYY-MM-DD HH:MM'(병원 현지 시간) → 시간대 있는 datetime. 형식이 틀리면 ValueError."""
    return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)


def to_utc_iso(text: str) -> str:
    return parse_local_slot(text).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def required_consents(draft: JSON) -> list[str]:
    """요청서마다 받아야 하는 동의 (계약 6절).

    - privacy: 이 요청서 내용을 고른 병원에 전달하는 데 대한 동의 (항상)
    - health: 건강정보(health_info)를 적었을 때
    - overseas_transfer: 한국어가 아닌 글을 번역하느라 해외 AI 서비스를 쓰는 경우 — 우리 가정이며
      개인정보보호위원회 질의 8번 회신 후 확정
    """
    kinds = ["privacy"]
    if draft.get("health_info"):
        kinds.append("health")
    if draft.get("language") != "ko":
        kinds.append("overseas_transfer")
    return kinds


def to_booking_create(draft: JSON, patient_timezone: str) -> JSON:
    """챗봇 초안 → 백엔드 `BookingCreate` 모양 (계약 6절). 진료과 코드 통일 전이라 department_code 대신 department 이름을 넣는다."""
    return {
        "department": draft["department"],  # TODO 진료과 코드 통일 후 department_code
        "preferred_slots": [to_utc_iso(s) for s in draft["preferred_slots"]],
        "patient_timezone": patient_timezone,
        "lang": draft["language"],
        "nationality": draft["nationality"],
        "contact_method": draft.get("contact_method", "email"),
        "visa_needed": draft["visa_needed"],
        "message": draft["inquiry"],
        "health_info": draft.get("health_info"),
    }


class BookingStore:
    def __init__(self, seed: list[JSON] | None = None):
        self._rows: list[JSON] = copy.deepcopy(fd.BOOKINGS if seed is None else seed)
        self._seq = itertools.count(1)

    # ------------------------------------------------------------ 읽기
    def list_for_patient(self, patient_id: str, status: str | None = None) -> list[JSON]:
        rows = [r for r in self._rows if r["patient_id"] == patient_id and (status is None or r["status"] == status)]
        names = {h["id"]: h["name_en"] for h in fd.HOSPITALS}
        return [{**copy.deepcopy(r), "hospital_name_en": names.get(r["hospital_id"])} for r in rows]

    def get_for_patient(self, patient_id: str, booking_id: str) -> JSON:
        for r in self._rows:
            if r["id"] == booking_id and r["patient_id"] == patient_id:
                return r
        raise BookingError("not_found", "내 예약에서 찾을 수 없습니다")  # 남의 것도 404 (계약 4절)

    # ------------------------------------------------------------ 환자가 제출
    def create_request(
        self,
        patient_id: str | None,
        draft: JSON,
        consents: list[JSON],
        *,
        residency: str | None,
        patient_timezone: str = "UTC",
        today: datetime | None = None,
    ) -> JSON:
        if not patient_id:
            raise BookingError("auth.required", "로그인이 필요합니다")
        if residency == "resident":
            raise BookingError("booking.not_available", "국내 거주 외국인은 이 경로로 요청할 수 없습니다")
        if residency is None:
            raise BookingError("validation", "체류 형태가 확인되지 않았습니다", {"missing": ["residency"]})

        hospital = next((h for h in fd.HOSPITALS if h["id"] == draft.get("hospital_id")), None)
        if hospital is None:
            raise BookingError("not_found", "병원을 찾을 수 없습니다")
        if not hospital["is_registered_facility"]:
            raise BookingError("booking.not_available", "외국인환자 유치의료기관으로 등록되지 않은 병원입니다")

        missing = [k for k in ("preferred_slots", "language", "nationality", "inquiry", "department") if not draft.get(k)]
        if draft.get("visa_needed") is None:
            missing.append("visa_needed")
        if missing:
            raise BookingError("validation", "요청서 칸이 비어 있습니다", {"missing": missing})
        slots = draft["preferred_slots"]
        if not 1 <= len(slots) <= 3:
            raise BookingError("validation", "희망 일시는 1~3개여야 합니다")
        try:
            payload = to_booking_create(draft, patient_timezone)
        except ValueError as e:
            raise BookingError("validation", f"희망 일시 형식 오류: {e}") from e
        now = today or datetime.now(timezone.utc)
        if any(parse_local_slot(s) <= now for s in slots):
            raise BookingError("validation", "이미 지난 일시가 있습니다")

        needed = required_consents(draft)
        given = {c.get("kind") for c in consents if c.get("version")}
        lacking = [k for k in needed if k not in given]
        if lacking:
            raise BookingError("consent.required", "필수 동의가 없습니다", {"missing": lacking})

        if any(r["patient_id"] == patient_id and r["hospital_id"] == hospital["id"] and r["status"] in OPEN_STATUSES
               for r in self._rows):
            raise BookingError("booking.duplicate", "같은 병원에 처리 안 된 요청이 이미 있습니다")

        row = {
            "id": f"demo-bk-new-{next(self._seq):03d}",
            "patient_id": patient_id,
            "hospital_id": hospital["id"],
            "status": "pending",
            "preferred": list(slots),
            "created_at": now.strftime("%Y-%m-%d"),
            "request": payload,  # BookingCreate 모양
            "consents": [{"kind": c["kind"], "version": c["version"]} for c in consents if c.get("kind") in needed],
            "events": [{"status": "pending", "actor": "patient"}],
        }
        self._rows.append(row)
        return {**copy.deepcopy(row), "hospital_name_en": hospital["name_en"]}

    # ------------------------------------------------------------ 상태 변경 (병원·환자) — 시연·테스트용
    def _transition(self, booking_id: str, action: str, actor: str, patient_id: str | None = None) -> JSON:
        row = next((r for r in self._rows if r["id"] == booking_id), None)
        if row is None or (patient_id is not None and row["patient_id"] != patient_id):
            raise BookingError("not_found", "예약을 찾을 수 없습니다")
        nxt = TRANSITIONS.get((row["status"], action))
        if nxt is None:
            raise BookingError("booking.invalid_transition", f"{row['status']}에서는 {action}할 수 없습니다")
        row["status"] = nxt
        row.setdefault("events", []).append({"status": nxt, "actor": actor})
        return row

    def hospital_respond(self, booking_id: str, action: str, slot: str | None = None) -> JSON:
        """병원 직원이 확정(confirm)·거절(reject)·다른 시간 제안(propose). 실제로는 병원 대시보드가 부른다."""
        if action not in ("confirm", "reject", "propose"):
            raise BookingError("validation", "병원 행동은 confirm/reject/propose")
        row = self._transition(booking_id, action, "hospital")
        if action == "confirm":
            row["confirmed_slot"] = row["preferred"][0]
        if action == "propose":
            if not slot:
                raise BookingError("validation", "제안할 일시가 필요합니다")
            row["proposed_slot"] = slot
        return copy.deepcopy(row)

    def patient_respond(self, patient_id: str, booking_id: str, action: str) -> JSON:
        if action not in ("accept", "cancel"):
            raise BookingError("validation", "환자 행동은 accept/cancel")
        row = self._transition(booking_id, action, "patient", patient_id)
        if action == "accept":
            row["confirmed_slot"] = row.get("proposed_slot")
        return copy.deepcopy(row)
