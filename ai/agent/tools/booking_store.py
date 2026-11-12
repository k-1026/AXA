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
from typing import Any, Protocol

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
    if (draft.get("lang") or draft.get("language")) != "ko":  # 요청서 payload는 lang, 챗봇 초안은 language
        kinds.append("overseas_transfer")
    return kinds


def to_booking_create(draft: JSON, patient_timezone: str) -> JSON:
    """챗봇 초안 → 백엔드 `BookingCreate` 모양 (계약 6절). `consents`는 환자가 체크한 뒤 제출 때 붙인다."""
    return {
        "department_code": draft["department_code"],  # departments.code (= 프론트 키)
        "preferred_slots": [to_utc_iso(s) for s in draft["preferred_slots"]],
        "patient_timezone": patient_timezone,
        "lang": draft["language"],
        "nationality": draft["nationality"],
        "contact_method": draft.get("contact_method", "email"),
        "visa_needed": draft["visa_needed"],
        "message": draft["inquiry"],
        "health_info": draft.get("health_info"),
    }


def utc_iso_to_local(text: str) -> str:
    """UTC ISO → 병원 현지(KST) 'YYYY-MM-DD HH:MM'."""
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M")


def _utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


class BookingGateway(Protocol):
    """서비스·도구가 쓰는 예약 조회 (읽기 전용). 지금은 `BookingStore`(가짜), 7b에서 `booking.service` 어댑터로 교체.
    - get_for_patient는 없거나 남의 것이면 `BookingError("not_found")`를 낸다
    - 어댑터는 DB·`AppError` 같은 예외를 `BookingError`로 바꿔서 낸다 (도구 run()은 그 밖의 예외를 "internal"로만 돌려줌)
    - 반환 dict 키: id, hospital_id, hospital_name_en, status, preferred, created_at (목록 순서는 정하지 않음)"""

    def list_for_patient(self, patient_id: str, status: str | None = None) -> list[JSON]: ...

    def get_for_patient(self, patient_id: str, booking_id: str) -> JSON: ...


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
                return copy.deepcopy(r)
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
        """챗봇 초안으로 제출 (시연·eval용 지름길). 체류 형태는 요청서 API에는 없는 칸이라 여기서만 검사한다."""
        if not patient_id:
            raise BookingError("auth.required", "로그인이 필요합니다")
        if residency == "resident":
            raise BookingError("booking.not_available", "국내 거주 외국인은 이 경로로 요청할 수 없습니다")
        if residency is None:
            raise BookingError("validation", "체류 형태가 확인되지 않았습니다", {"missing": ["residency"]})
        try:
            payload = to_booking_create(draft, patient_timezone)
        except (KeyError, ValueError) as e:
            raise BookingError("validation", f"요청서 칸 오류: {e}") from e
        return self.create_from_payload(patient_id, draft.get("hospital_id"), payload, consents, today=today)

    def create_from_payload(
        self,
        patient_id: str | None,
        hospital_id: int | None,
        payload: JSON,
        consents: list[JSON],
        *,
        today: datetime | None = None,
    ) -> JSON:
        """`POST /hospitals/{id}/booking-requests` (사람이 쓰는 것과 같은 API)가 하는 일을 흉내 낸다.
        payload = BookingCreate 모양(계약 6절), consents = [{"kind", "version"}]. 백엔드가 생기면 이 함수만 교체."""
        if not patient_id:
            raise BookingError("auth.required", "로그인이 필요합니다")
        hospital = next((h for h in fd.HOSPITALS if h["id"] == hospital_id), None)
        if hospital is None:
            raise BookingError("not_found", "병원을 찾을 수 없습니다")
        if not hospital["is_registered_facility"]:
            raise BookingError("booking.not_available", "외국인환자 유치의료기관으로 등록되지 않은 병원입니다")

        missing = [k for k in ("department_code", "preferred_slots", "lang", "nationality", "message") if not payload.get(k)]
        if payload.get("visa_needed") is None:
            missing.append("visa_needed")
        if missing:
            raise BookingError("validation", "요청서 칸이 비어 있습니다", {"missing": missing})
        slots = payload["preferred_slots"]
        if not 1 <= len(slots) <= 3:
            raise BookingError("validation", "희망 일시는 1~3개여야 합니다")
        try:
            slot_times = [_utc(x) for x in slots]
        except ValueError as e:
            raise BookingError("validation", f"희망 일시 형식 오류: {e}") from e
        now = today or datetime.now(timezone.utc)
        if any(t <= now for t in slot_times):
            raise BookingError("validation", "이미 지난 일시가 있습니다")

        needed = required_consents(payload)
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
            "preferred": [utc_iso_to_local(x) for x in slots],
            "created_at": now.strftime("%Y-%m-%d"),
            "request": copy.deepcopy(payload),  # BookingCreate 모양
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
