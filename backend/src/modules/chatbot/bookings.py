"""챗봇이 쓰는 예약 조회(`BookingGateway`, ai/agent/service.py)의 백엔드 구현.

`booking` 모듈(B 주인)이 아직 없어서 **지금은 "내 요청 없음"으로 답한다**. 가짜 예약 데이터(`BookingStore`)를
실제 환자에게 보여 주면 안 되므로 쓰지 않는다. B가 계약 5절의 `booking.service.list_for_patient`·`get_for_patient`를
만들면 이 파일만 그 함수를 부르도록 바꾼다 (반환 값을 dict로 바꾸는 어댑터).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ai.agent.session_store import JSON
from ai.agent.tools.booking_store import BookingError


class BookingGateway:
    def __init__(self, db: Session):
        self.db = db

    def list_for_patient(self, patient_id: str, status: str | None = None) -> list[JSON]:
        return []  # TODO(B의 booking.service 생기면): booking.service.list_for_patient(self.db, patient_id, status)

    def get_for_patient(self, patient_id: str, booking_id: str) -> JSON:
        raise BookingError("not_found", "요청을 찾을 수 없습니다")
