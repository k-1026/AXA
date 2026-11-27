"""챗봇이 쓰는 예약 조회(`BookingGateway`, ai/agent/service.py)의 백엔드 구현.

`booking.service.list_for_patient`·`get_for_patient`(계약 5절, B 모듈)를 불러 챗봇 도구가 쓰는 dict로 바꾸는 어댑터.
상대 모듈은 이 파일 한 곳에서만 부른다 (contracts 5절). 모양은 가짜 저장소(`ai/agent/tools/booking_store.py`)와 같게:
`id`·`hospital_id`·`hospital_name_en`·`status`·`preferred`·`confirmed_slot`·`proposed_slot`·`created_at`·`visited`
(시간은 병원 현지 = 한국 시간 "YYYY-MM-DD HH:MM"). 요청서 원문·동의·답장은 넘기지 않는다 (모델에 보낼 필요 없음).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.agent.session_store import JSON
from ai.agent.tools.booking_store import BookingError
from core.errors import AppError
from modules.aftercare import service as aftercare_service
from modules.booking import service as booking_service
from modules.booking.models import BookingRequest
from modules.hospital.models import Hospital

KST = ZoneInfo("Asia/Seoul")


def _kst(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if dt.tzinfo is None:  # SQLite는 시간대를 빼고 돌려줌 → 저장 규칙대로 UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def _row(req: BookingRequest, names: dict[int, str | None]) -> JSON:
    slot = _kst(req.confirmed_slot)
    return {
        "id": str(req.id),
        "hospital_id": req.hospital_id,
        "hospital_name_en": names.get(req.hospital_id),
        "status": req.status,
        "preferred": [s for s in (_kst(x) for x in req.preferred_slots or []) if s],
        # confirmed_slot 칸은 확정 시간과 병원이 제안한 시간을 같이 담음 (booking/models.py)
        "confirmed_slot": slot if req.status in ("confirmed", "visited", "no_show", "paid") else None,
        "proposed_slot": slot if req.status == "proposed" else None,
        "created_at": _kst(req.created_at),
        "visited": req.status in ("visited", "paid"),
    }


def _names(db: Session, ids: set[int]) -> dict[int, str | None]:
    if not ids:
        return {}
    return {h.id: h.name_en for h in db.scalars(select(Hospital).where(Hospital.id.in_(ids)))}


def _uuid(patient_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(patient_id))
    except ValueError:
        return None


class BookingGateway:
    def __init__(self, db: Session):
        self.db = db

    def list_for_patient(self, patient_id: str, status: str | None = None) -> list[JSON]:
        pid = _uuid(patient_id)
        if pid is None:
            return []
        reqs = [r for r in booking_service.list_for_patient(self.db, pid) if status is None or r.status == status]
        names = _names(self.db, {r.hospital_id for r in reqs})
        return [_row(r, names) for r in reqs]

    def get_for_patient(self, patient_id: str, booking_id: str) -> JSON:
        pid, bid = _uuid(patient_id), _uuid(booking_id)
        if pid is None or bid is None:
            raise BookingError("not_found", "요청을 찾을 수 없습니다")
        try:
            req = booking_service.get_for_patient(self.db, pid, bid)
        except AppError as e:  # 남의 요청도 404 (계약 4절)
            raise BookingError("not_found", "요청을 찾을 수 없습니다") from e
        return _row(req, _names(self.db, {req.hospital_id}))

    def aftercare_for(self, patient_id: str, booking_id: str) -> JSON:
        """챗봇 사후관리 카드용: 사후관리 대화를 열 수 있는지 + 이미 있는 대화 id. 메시지는 보내지 않음."""
        pid, bid = _uuid(patient_id), _uuid(booking_id)
        if pid is None or bid is None:
            return {"available": False}
        try:
            aftercare_service.patient_upload_prefix(self.db, pid, bid)  # 방문 완료 + 사후관리 지원 병원인지 (아니면 404·409)
        except AppError:
            return {"available": False}
        try:
            thread, _ = aftercare_service.patient_messages(self.db, pid, bid)
            return {"available": True, "thread_id": str(thread.id)}
        except AppError:  # 아직 대화 없음
            return {"available": True, "thread_id": None}
